import logging
import os
import requests
import json
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import time

logger = logging.getLogger(__name__)

class ZohoDeskAuth:
    """Handles Zoho Desk OAuth 2.0 authentication and token management"""
    
    def __init__(self, 
                 client_id: str = None,
                 client_secret: str = None,
                 refresh_token: str = None,
                 domain: str = "com"):
        
        self.client_id = client_id or os.environ.get("ZOHO_CLIENT_ID")
        self.client_secret = client_secret or os.environ.get("ZOHO_CLIENT_SECRET")
        self.refresh_token = refresh_token or os.environ.get("ZOHO_REFRESH_TOKEN")
        self.domain = domain or os.environ.get("ZOHO_DOMAIN", "com")
        
        # OAuth endpoints based on domain
        self.oauth_base_url = f"https://accounts.zoho.{self.domain}/oauth/v2"
        
        # Token storage
        self.access_token = None
        self.token_expires_at = None
        
        if not all([self.client_id, self.client_secret, self.refresh_token]):
            logger.warning("Missing Zoho OAuth credentials. Some functionality may be limited.")
    
    def get_access_token(self) -> Optional[str]:
        """Get a valid access token, refreshing if necessary"""
        if self._is_token_valid():
            return self.access_token
        
        return self._refresh_access_token()
    
    def _is_token_valid(self) -> bool:
        """Check if the current access token is still valid"""
        if not self.access_token or not self.token_expires_at:
            return False
        
        # Check if token expires in the next 5 minutes (buffer time)
        buffer_time = datetime.now() + timedelta(minutes=5)
        return self.token_expires_at > buffer_time
    
    def _refresh_access_token(self) -> Optional[str]:
        """Refresh the access token using the refresh token"""
        if not self.refresh_token:
            logger.error("No refresh token available")
            return None
        
        try:
            url = f"{self.oauth_base_url}/token"
            
            data = {
                'grant_type': 'refresh_token',
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'refresh_token': self.refresh_token
            }
            
            response = requests.post(url, data=data, timeout=30)
            response.raise_for_status()
            
            token_data = response.json()
            
            if 'access_token' in token_data:
                self.access_token = token_data['access_token']
                
                # Calculate expiry time (default to 1 hour if not provided)
                expires_in = token_data.get('expires_in', 3600)
                self.token_expires_at = datetime.now() + timedelta(seconds=expires_in)
                
                logger.info("Access token refreshed successfully")
                return self.access_token
            else:
                logger.error(f"Failed to get access token: {token_data}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to refresh access token: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error during token refresh: {e}")
            return None
    
    def get_auth_headers(self) -> Dict[str, str]:
        """Get HTTP headers with authentication"""
        token = self.get_access_token()
        if not token:
            raise Exception("Unable to obtain valid access token")
        
        return {
            'Authorization': f'Zoho-oauthtoken {token}',
            'Content-Type': 'application/json'
        }
    
    def test_authentication(self) -> bool:
        """Test if authentication is working"""
        try:
            token = self.get_access_token()
            return token is not None
        except Exception as e:
            logger.error(f"Authentication test failed: {e}")
            return False
