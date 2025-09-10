import logging
import os
from typing import List, Dict, Any, Optional
from atlassian import Jira

logger = logging.getLogger(__name__)

class JiraClient:
    """Client for interacting with Jira API"""
    
    def __init__(self, 
                 url: str = None, 
                 username: str = None, 
                 api_token: str = None):
        
        self.url = url or os.environ.get("JIRA_URL")
        self.username = username or os.environ.get("JIRA_USERNAME")
        self.api_token = api_token or os.environ.get("JIRA_API_TOKEN")
        
        if not all([self.url, self.username, self.api_token]):
            raise ValueError("Missing Jira credentials")
        
        self.client = Jira(
            url=self.url,
            username=self.username,
            password=self.api_token,
            timeout=60
        )
        
        logger.info(f"Initialized Jira client for {self.url}")
    
    def get_projects(self) -> List[Dict[str, Any]]:
        """Get all accessible projects"""
        try:
            projects = self.client.projects()
            logger.info(f"Found {len(projects)} projects")
            return projects
        except Exception as e:
            logger.error(f"Failed to get projects: {e}")
            return []
    
    def get_resolved_issues(self, project_key: str = None, days: int = 30, limit: int = 100) -> List[Dict[str, Any]]:
        """Get resolved issues for knowledge base"""
        try:
            from datetime import datetime, timedelta
            
            since_date = datetime.now() - timedelta(days=days)
            date_str = since_date.strftime('%Y-%m-%d')
            
            # Build JQL query
            jql = f'resolved >= "{date_str}" AND resolution != Unresolved'
            if project_key:
                jql = f'project = {project_key} AND {jql}'
            
            issues = self.client.jql(jql, limit=limit)
            
            resolved_issues = []
            for issue in issues.get('issues', []):
                # Only include issues with descriptions or comments
                if issue.get('fields', {}).get('description'):
                    resolved_issues.append(issue)
            
            logger.info(f"Found {len(resolved_issues)} resolved issues with content")
            return resolved_issues
            
        except Exception as e:
            logger.error(f"Failed to get resolved issues: {e}")
            return []
    
    def test_connection(self) -> bool:
        """Test if connection to Jira is working"""
        try:
            projects = self.client.projects()
            logger.info("Jira connection test successful")
            return True
        except Exception as e:
            logger.error(f"Jira connection test failed: {e}")
            return False
