import logging
import os
from typing import List, Dict, Any, Optional
from atlassian import Confluence

logger = logging.getLogger(__name__)

class ConfluenceClient:
    """Client for interacting with Confluence API"""
    
    def __init__(self, 
                 url: str = None, 
                 username: str = None, 
                 api_token: str = None):
        
        self.url = url or os.environ.get("CONFLUENCE_URL")
        self.username = username or os.environ.get("CONFLUENCE_USERNAME")
        self.api_token = api_token or os.environ.get("CONFLUENCE_API_TOKEN")
        
        if not all([self.url, self.username, self.api_token]):
            raise ValueError("Missing Confluence credentials")
        
        self.client = Confluence(
            url=self.url,
            username=self.username,
            password=self.api_token,
            timeout=60
        )
        
        logger.info(f"Initialized Confluence client for {self.url}")
    
    def get_spaces(self) -> List[Dict[str, Any]]:
        """Get all accessible spaces"""
        try:
            spaces = self.client.get_all_spaces(start=0, limit=100)
            logger.info(f"Found {len(spaces)} spaces")
            return spaces
        except Exception as e:
            logger.error(f"Failed to get spaces: {e}")
            return []
    
    def get_space_pages(self, space_key: str, limit: int = 500) -> List[Dict[str, Any]]:
        """Get all pages from a specific space"""
        try:
            pages = self.client.get_all_pages_from_space(
                space=space_key, 
                start=0, 
                limit=limit,
                expand='version,space,body.storage'
            )
            logger.info(f"Found {len(pages)} pages in space {space_key}")
            return pages
        except Exception as e:
            logger.error(f"Failed to get pages from space {space_key}: {e}")
            return []
    
    def get_page_content(self, page_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed page content"""
        try:
            page = self.client.get_page_by_id(
                page_id=page_id,
                expand='body.storage,version,space,ancestors'
            )
            return page
        except Exception as e:
            logger.error(f"Failed to get page {page_id}: {e}")
            return None
    
    def get_recently_updated_pages(self, days: int = 7, limit: int = 100) -> List[Dict[str, Any]]:
        """Get pages updated in the last N days"""
        try:
            # Note: This is a simplified approach - in practice you might want to use CQL
            from datetime import datetime, timedelta
            
            since = datetime.now() - timedelta(days=days)
            
            # Get all pages and filter by date (not efficient for large instances)
            all_spaces = self.get_spaces()
            recent_pages = []
            
            for space in all_spaces:
                space_key = space.get('key')
                if not space_key:
                    continue
                
                pages = self.get_space_pages(space_key, limit=limit)
                for page in pages:
                    version_info = page.get('version', {})
                    if version_info.get('when'):
                        # Parse Confluence date format
                        try:
                            page_date = datetime.fromisoformat(
                                version_info['when'].replace('Z', '+00:00')
                            )
                            if page_date >= since:
                                recent_pages.append(page)
                        except Exception as e:
                            logger.debug(f"Failed to parse date for page {page.get('id')}: {e}")
                
                # Limit total pages to avoid overwhelming the system
                if len(recent_pages) >= limit:
                    break
            
            logger.info(f"Found {len(recent_pages)} recently updated pages")
            return recent_pages
            
        except Exception as e:
            logger.error(f"Failed to get recently updated pages: {e}")
            return []
    
    def test_connection(self) -> bool:
        """Test if connection to Confluence is working"""
        try:
            spaces = self.client.get_all_spaces(start=0, limit=1)
            logger.info("Confluence connection test successful")
            return True
        except Exception as e:
            logger.error(f"Confluence connection test failed: {e}")
            return False
