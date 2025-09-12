import logging
import os
import requests
import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import time
from urllib.parse import urlencode

from zoho_desk_module.zoho_auth import ZohoDeskAuth

logger = logging.getLogger(__name__)

class ZohoDeskClient:
    """Client for interacting with Zoho Desk API"""
    
    def __init__(self, 
                 org_id: str = None,
                 domain: str = "com",
                 auth: ZohoDeskAuth = None):
        
        self.org_id = org_id or os.environ.get("ZOHO_ORG_ID")
        self.domain = domain or os.environ.get("ZOHO_DOMAIN", "com")
        
        if not self.org_id:
            raise ValueError("Zoho Org ID is required")
        
        # Initialize authentication
        self.auth = auth or ZohoDeskAuth(domain=self.domain)
        
        # API configuration
        self.api_base_url = f"https://desk.zoho.{self.domain}/api/v1"
        self.session = requests.Session()
        
        logger.info(f"Initialized Zoho Desk client for org {self.org_id}")
    
    def _make_request(self, method: str, endpoint: str, params: Dict = None, data: Dict = None) -> Optional[Dict]:
        """Make authenticated request to Zoho Desk API"""
        try:
            headers = self.auth.get_auth_headers()
            url = f"{self.api_base_url}/{endpoint.lstrip('/')}"
            
            # Add org_id to headers
            headers['orgId'] = self.org_id
            
            response = self.session.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=data,
                timeout=60
            )
            
            # Handle rate limiting
            if response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', 60))
                logger.warning(f"Rate limited. Waiting {retry_after} seconds")
                time.sleep(retry_after)
                return self._make_request(method, endpoint, params, data)
            
            response.raise_for_status()
            
            return response.json() if response.content else {}
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {method} {endpoint} - {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in API request: {e}")
            return None
    
    def get_tickets(self, 
                   limit: int = 100,
                   from_date: datetime = None,
                   to_date: datetime = None,
                   status: str = None,
                   department_id: str = None) -> List[Dict[str, Any]]:
        """Get tickets with optional filtering"""
        try:
            params = {
                'limit': min(limit, 100),  # API max is 100 per request
                'from': 0
            }
            
            # Add date filters
            if from_date:
                params['createdTime'] = from_date.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
            
            if status:
                params['status'] = status
            
            if department_id:
                params['departmentId'] = department_id
            
            all_tickets = []
            from_index = 0
            
            while len(all_tickets) < limit:
                params['from'] = from_index
                params['limit'] = min(100, limit - len(all_tickets))
                
                response = self._make_request('GET', '/tickets', params=params)
                
                if not response or 'data' not in response:
                    break
                
                tickets = response['data']
                if not tickets:
                    break
                
                all_tickets.extend(tickets)
                from_index += len(tickets)
                
                # Check if we have all available tickets
                if len(tickets) < params['limit']:
                    break
            
            logger.info(f"Retrieved {len(all_tickets)} tickets")
            return all_tickets
            
        except Exception as e:
            logger.error(f"Failed to get tickets: {e}")
            return []
    
    def get_ticket_details(self, ticket_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific ticket"""
        try:
            response = self._make_request('GET', f'/tickets/{ticket_id}')
            return response
        except Exception as e:
            logger.error(f"Failed to get ticket details for {ticket_id}: {e}")
            return None
    
    def get_ticket_conversations(self, ticket_id: str) -> List[Dict[str, Any]]:
        """Get all conversations/threads for a ticket"""
        try:
            response = self._make_request('GET', f'/tickets/{ticket_id}/conversations')
            
            if response and 'data' in response:
                conversations = response['data']
                logger.debug(f"Retrieved {len(conversations)} conversations for ticket {ticket_id}")
                return conversations
            
            return []
            
        except Exception as e:
            logger.error(f"Failed to get conversations for ticket {ticket_id}: {e}")
            return []
    
    def get_ticket_history(self, ticket_id: str) -> List[Dict[str, Any]]:
        """Get history/activity log for a ticket"""
        try:
            response = self._make_request('GET', f'/tickets/{ticket_id}/history')
            
            if response and 'data' in response:
                history = response['data']
                logger.debug(f"Retrieved {len(history)} history entries for ticket {ticket_id}")
                return history
            
            return []
            
        except Exception as e:
            logger.error(f"Failed to get history for ticket {ticket_id}: {e}")
            return []
    
    def get_recently_updated_tickets(self, days: int = 7, limit: int = 100) -> List[Dict[str, Any]]:
        """Get tickets updated in the last N days"""
        try:
            from_date = datetime.now() - timedelta(days=days)
            
            # Use modifiedTime for recently updated tickets
            params = {
                'limit': min(limit, 100),
                'modifiedTime': from_date.strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
                'sortBy': 'modifiedTime'
            }
            
            response = self._make_request('GET', '/tickets', params=params)
            
            if response and 'data' in response:
                tickets = response['data']
                logger.info(f"Found {len(tickets)} recently updated tickets")
                return tickets
            
            return []
            
        except Exception as e:
            logger.error(f"Failed to get recently updated tickets: {e}")
            return []
    
    def get_resolved_tickets(self, days: int = 30, limit: int = 100) -> List[Dict[str, Any]]:
        """Get resolved tickets for knowledge base building"""
        try:
            from_date = datetime.now() - timedelta(days=days)
            
            # Get resolved tickets
            resolved_tickets = self.get_tickets(
                limit=limit,
                from_date=from_date,
                status='Closed'  # or 'Resolved' depending on your setup
            )
            
            logger.info(f"Found {len(resolved_tickets)} resolved tickets")
            return resolved_tickets
            
        except Exception as e:
            logger.error(f"Failed to get resolved tickets: {e}")
            return []
    
    def get_departments(self) -> List[Dict[str, Any]]:
        """Get all departments in the organization"""
        try:
            response = self._make_request('GET', '/departments')
            
            if response and 'data' in response:
                departments = response['data']
                logger.info(f"Retrieved {len(departments)} departments")
                return departments
            
            return []
            
        except Exception as e:
            logger.error(f"Failed to get departments: {e}")
            return []
    
    def test_connection(self) -> bool:
        """Test if connection to Zoho Desk is working"""
        try:
            # Try to get a small number of tickets as a connection test
            response = self._make_request('GET', '/tickets', params={'limit': 1})
            
            if response is not None:
                logger.info("Zoho Desk connection test successful")
                return True
            else:
                logger.error("Zoho Desk connection test failed")
                return False
                
        except Exception as e:
            logger.error(f"Zoho Desk connection test failed: {e}")
            return False
