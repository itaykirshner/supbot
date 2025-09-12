import logging
import os
from typing import List, Dict, Any, Optional
from atlassian import Confluence
import requests

logger = logging.getLogger(__name__)

class ConfluenceClient:
    """Client for interacting with Confluence API"""
    
    def __init__(self, 
                 url: str = None, 
                 username: str = None, 
                 api_token: str = None,
                 cloud_id: str = None):
        
        self.base_url = url or os.environ.get("CONFLUENCE_URL")
        self.username = username or os.environ.get("CONFLUENCE_USERNAME")
        self.api_token = api_token or os.environ.get("CONFLUENCE_API_TOKEN")
        self.cloud_id = cloud_id or os.environ.get("CONFLUENCE_CLOUD_ID")
        
        if not all([self.base_url, self.username, self.api_token]):
            raise ValueError("Missing Confluence credentials")
        
        # Determine if we should use Cloud API or direct instance API
        self.use_cloud_api = bool(self.cloud_id)
        
        if self.use_cloud_api:
            logger.info(f"Using Atlassian Cloud API for cloud ID: {self.cloud_id}")
            self.api_base_url = f"https://api.atlassian.com/ex/confluence/{self.cloud_id}"
            # For Cloud API, we'll use requests directly
            self.session = requests.Session()
            self.session.auth = (self.username, self.api_token)
            self.session.headers.update({
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            })
        else:
            logger.info(f"Using direct instance API for: {self.base_url}")
            try:
                self.client = Confluence(
                    url=self.base_url,
                    username=self.username,
                    password=self.api_token,
                    timeout=60
                )
            except Exception as e:
                logger.error(f"Failed to initialize Confluence client: {e}")
                # Try with cloud API as fallback
                logger.info("Attempting to determine cloud ID automatically...")
                self._try_cloud_api_fallback()
        
        logger.info(f"Initialized Confluence client")
    
    def _try_cloud_api_fallback(self):
        """Try to extract cloud ID and use Cloud API as fallback"""
        try:
            # Extract potential cloud ID from the base URL or try to determine it
            if 'atlassian.net' in self.base_url:
                # This is likely a cloud instance, try to get accessible resources
                import re
                
                # Try to get accessible resources to find cloud ID
                auth = (self.username, self.api_token)
                response = requests.get(
                    'https://api.atlassian.com/oauth/token/accessible-resources',
                    auth=auth,
                    headers={'Accept': 'application/json'},
                    timeout=30
                )
                
                if response.status_code == 200:
                    resources = response.json()
                    for resource in resources:
                        if 'confluence' in resource.get('name', '').lower() or \
                           self.base_url.split('.')[0].split('//')[-1] in resource.get('name', '').lower():
                            self.cloud_id = resource['id']
                            logger.info(f"Auto-detected cloud ID: {self.cloud_id}")
                            break
                    
                    if self.cloud_id:
                        self.use_cloud_api = True
                        self.api_base_url = f"https://api.atlassian.com/ex/confluence/{self.cloud_id}"
                        self.session = requests.Session()
                        self.session.auth = (self.username, self.api_token)
                        self.session.headers.update({
                            'Accept': 'application/json',
                            'Content-Type': 'application/json'
                        })
                        return
                        
        except Exception as e:
            logger.warning(f"Could not auto-detect cloud ID: {e}")
        
        raise Exception("Could not initialize Confluence client with direct API or Cloud API")
    
    def _make_request(self, endpoint: str, params: dict = None) -> Optional[dict]:
        """Make API request using appropriate method"""
        if self.use_cloud_api:
            return self._make_cloud_api_request(endpoint, params)
        else:
            return self._make_direct_api_request(endpoint, params)
    
    def _make_cloud_api_request(self, endpoint: str, params: dict = None) -> Optional[dict]:
        """Make request using Atlassian Cloud API"""
        try:
            url = f"{self.api_base_url}/wiki/rest/api/{endpoint.lstrip('/')}"
            response = self.session.get(url, params=params, timeout=60)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Cloud API request failed for {endpoint}: {e}")
            return None
    
    def _make_direct_api_request(self, endpoint: str, params: dict = None) -> Optional[dict]:
        """Make request using direct instance API (atlassian-python-api)"""
        try:
            # Map common endpoints to atlassian-python-api methods
            if endpoint == 'space':
                return {'results': self.client.get_all_spaces(start=params.get('start', 0), 
                                                            limit=params.get('limit', 50))}
            elif endpoint.startswith('space/') and '/content' in endpoint:
                space_key = endpoint.split('/')[1]
                return {'results': self.client.get_all_pages_from_space(
                    space=space_key,
                    start=params.get('start', 0),
                    limit=params.get('limit', 50),
                    expand='body.storage,version,space'
                )}
            elif endpoint.startswith('content/'):
                content_id = endpoint.split('/')[1]
                return self.client.get_page_by_id(
                    page_id=content_id,
                    expand='body.storage,version,space,ancestors'
                )
            else:
                # For other endpoints, we'd need to implement specific mappings
                logger.warning(f"Direct API mapping not implemented for endpoint: {endpoint}")
                return None
        except Exception as e:
            logger.error(f"Direct API request failed for {endpoint}: {e}")
            return None
    
    def get_spaces(self, space_keys: List[str] = None) -> List[Dict[str, Any]]:
        """Get accessible spaces, optionally filtered by space keys"""
        try:
            if space_keys:
                # If specific spaces requested, validate they exist and get their details
                spaces = []
                for space_key in space_keys:
                    space_info = self.get_space_info(space_key)
                    if space_info:
                        spaces.append(space_info)
                logger.info(f"Retrieved {len(spaces)} specific spaces: {space_keys}")
                return spaces
            else:
                # Get all spaces with pagination
                all_spaces = []
                start = 0
                limit = 50  # Smaller limit for better pagination
                
                while True:
                    result = self._make_request('space', {'start': start, 'limit': limit})
                    if not result or 'results' not in result:
                        break
                    
                    spaces = result['results']
                    if not spaces:
                        break
                    
                    all_spaces.extend(spaces)
                    start += len(spaces)
                    
                    # Check if we've got all spaces
                    if len(spaces) < limit:
                        break
                
                logger.info(f"Retrieved {len(all_spaces)} spaces")
                return all_spaces
        except Exception as e:
            logger.error(f"Failed to get spaces: {e}")
            return []
    
    def get_space_info(self, space_key: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific space"""
        try:
            result = self._make_request(f'space/{space_key}')
            if result:
                logger.debug(f"Retrieved space info for: {space_key}")
                return result
            return None
        except Exception as e:
            logger.error(f"Failed to get space info for {space_key}: {e}")
            return None
    
    def get_space_pages(self, space_key: str, limit: int = 500) -> List[Dict[str, Any]]:
        """Get all pages from a specific space"""
        try:
            all_pages = []
            start = 0
            page_size = min(50, limit)  # API typically limits to 50 per request
            
            while len(all_pages) < limit:
                if self.use_cloud_api:
                    # For cloud API, use the content endpoint with space filter
                    params = {
                        'spaceKey': space_key,
                        'type': 'page',
                        'status': 'current',
                        'expand': 'body.storage,version,space',
                        'start': start,
                        'limit': page_size
                    }
                    result = self._make_request('content', params)
                else:
                    # For direct API, use the space/content endpoint
                    result = self._make_request(f'space/{space_key}/content', {
                        'start': start,
                        'limit': page_size,
                        'expand': 'body.storage,version,space'
                    })
                
                if not result or 'results' not in result:
                    break
                
                pages = result['results']
                if not pages:
                    break
                
                all_pages.extend(pages)
                start += len(pages)
                
                # If we got fewer results than requested, we've reached the end
                if len(pages) < page_size:
                    break
            
            # Limit to requested number
            all_pages = all_pages[:limit]
            logger.info(f"Found {len(all_pages)} pages in space {space_key}")
            return all_pages
            
        except Exception as e:
            logger.error(f"Failed to get pages from space {space_key}: {e}")
            return []
    
    def get_page_content(self, page_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed page content"""
        try:
            if self.use_cloud_api:
                result = self._make_request(f'content/{page_id}', {
                    'expand': 'body.storage,version,space,ancestors'
                })
            else:
                result = self._make_request(f'content/{page_id}')
            
            return result
        except Exception as e:
            logger.error(f"Failed to get page {page_id}: {e}")
            return None
    
    def get_recently_updated_pages(self, days: int = 7, limit: int = 100, space_keys: List[str] = None) -> List[Dict[str, Any]]:
        """Get pages updated in the last N days, optionally filtered by space keys"""
        try:
            from datetime import datetime, timedelta
            
            since = datetime.now() - timedelta(days=days)
            
            # Get spaces to check
            if space_keys:
                spaces = self.get_spaces(space_keys)
                logger.info(f"Checking recently updated pages in specific spaces: {space_keys}")
            else:
                spaces = self.get_spaces()
                logger.info(f"Checking recently updated pages in all spaces")
            
            recent_pages = []
            
            for space in spaces:
                space_key = space.get('key')
                if not space_key:
                    continue
                
                pages = self.get_space_pages(space_key, limit=min(limit, 50))
                for page in pages:
                    version_info = page.get('version', {})
                    if version_info.get('when'):
                        try:
                            # Parse Confluence date format
                            page_date = datetime.fromisoformat(
                                version_info['when'].replace('Z', '+00:00').replace('+0000', '+00:00')
                            )
                            if page_date >= since:
                                recent_pages.append(page)
                        except Exception as e:
                            logger.debug(f"Failed to parse date for page {page.get('id')}: {e}")
                
                # Stop if we have enough pages
                if len(recent_pages) >= limit:
                    break
            
            recent_pages = recent_pages[:limit]
            logger.info(f"Found {len(recent_pages)} recently updated pages")
            return recent_pages
            
        except Exception as e:
            logger.error(f"Failed to get recently updated pages: {e}")
            return []
    
    def test_connection(self) -> bool:
        """Test if connection to Confluence is working"""
        try:
            if self.use_cloud_api:
                # Test cloud API connection
                response = self.session.get(
                    f"{self.api_base_url}/wiki/rest/api/space",
                    params={'limit': 1},
                    timeout=30
                )
                response.raise_for_status()
                logger.info("Confluence Cloud API connection test successful")
                return True
            else:
                # Test direct API connection
                spaces = self.client.get_all_spaces(start=0, limit=1)
                logger.info("Confluence direct API connection test successful")
                return True
        except Exception as e:
            logger.error(f"Confluence connection test failed: {e}")
            return False