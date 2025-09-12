import asyncio
import logging
import os
import sys
import time
from pathlib import Path
from typing import List, Dict, Any

from rag_module.rag_client import add_document, add_documents_batch, delete_documents, health_check as rag_health_check, get_collection_stats
from confluence_client import ConfluenceClient
from jira_client import JiraClient
from data_processor import DataProcessor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SyncManager:
    """Manages the synchronization of data from external sources to vector database"""
    
    def __init__(self):
        # Initialize clients
        self.rag_client = None
        self.confluence_client = None
        self.jira_client = None
        
        # Configuration
        self.sync_confluence = os.environ.get("SYNC_CONFLUENCE", "true").lower() == "true"
        self.sync_jira = os.environ.get("SYNC_JIRA", "false").lower() == "true"  # Default off
        self.confluence_spaces = self._parse_space_list(os.environ.get("CONFLUENCE_SPACES", ""))
        self.jira_projects = self._parse_space_list(os.environ.get("JIRA_PROJECT_KEYS", ""))
        self.incremental_sync = os.environ.get("INCREMENTAL_SYNC", "true").lower() == "true"
        self.sync_days = int(os.environ.get("SYNC_DAYS", "7"))  # For incremental sync
        
        logger.info(f"Sync configuration: Confluence={self.sync_confluence}, Jira={self.sync_jira}")
        logger.info(f"Incremental sync: {self.incremental_sync}, Days: {self.sync_days}")
        logger.info(f"Confluence spaces: {self.confluence_spaces}")
        logger.info(f"Jira projects: {self.jira_projects}")
        logger.info(f"Environment variables:")
        logger.info(f"  SYNC_CONFLUENCE: {os.environ.get('SYNC_CONFLUENCE', 'not set')}")
        logger.info(f"  SYNC_JIRA: {os.environ.get('SYNC_JIRA', 'not set')}")
        logger.info(f"  CONFLUENCE_SPACES: {os.environ.get('CONFLUENCE_SPACES', 'not set')}")
        logger.info(f"  JIRA_PROJECT_KEYS: {os.environ.get('JIRA_PROJECT_KEYS', 'not set')}")
        logger.info(f"  INCREMENTAL_SYNC: {os.environ.get('INCREMENTAL_SYNC', 'not set')}")
        logger.info(f"  SYNC_DAYS: {os.environ.get('SYNC_DAYS', 'not set')}")
        
        self._initialize_clients()
    
    def _parse_space_list(self, space_string: str) -> List[str]:
        """Parse comma-separated list of Confluence spaces"""
        if not space_string:
            return []
        return [space.strip() for space in space_string.split(",") if space.strip()]
    
    def _initialize_clients(self):
        """Initialize all required clients"""
        try:
            # RAG client is now functional - no initialization needed
            logger.info("RAG client ready (functional approach)")
            
            # Initialize Confluence client if needed
            if self.sync_confluence:
                self.confluence_client = ConfluenceClient()
                if not self.confluence_client.test_connection():
                    raise Exception("Confluence connection test failed")
                logger.info("Confluence client initialized")
            
            # Initialize Jira client if needed
            if self.sync_jira:
                self.jira_client = JiraClient()
                if not self.jira_client.test_connection():
                    raise Exception("Jira connection test failed")
                logger.info("Jira client initialized")
                
        except Exception as e:
            logger.error(f"Failed to initialize clients: {e}")
            raise
    
    async def sync_confluence_data(self) -> int:
        """Sync Confluence pages to vector database"""
        if not self.confluence_client:
            logger.warning("Confluence client not initialized, skipping sync")
            return 0
        
        total_processed = 0
        
        try:
            # Determine which spaces to sync
            if self.confluence_spaces:
                # Sync specific spaces
                spaces_to_sync = self.confluence_spaces
                logger.info(f"Syncing specific spaces: {spaces_to_sync}")
            else:
                # Sync all spaces - get space keys from all spaces
                all_spaces = self.confluence_client.get_spaces()
                spaces_to_sync = [space['key'] for space in all_spaces if space.get('key')]
                logger.info(f"Syncing all {len(spaces_to_sync)} spaces")
            
            # Process each space
            for space_key in spaces_to_sync:
                logger.info(f"Processing space: {space_key}")
                
                try:
                    # Get pages based on sync type
                    if self.incremental_sync:
                        # Get recently updated pages for this specific space
                        pages = self.confluence_client.get_recently_updated_pages(
                            days=self.sync_days, 
                            limit=100,
                            space_keys=[space_key]  # Only check this specific space
                        )
                    else:
                        # Get all pages from this specific space
                        pages = self.confluence_client.get_space_pages(space_key)
                    
                    logger.info(f"Found {len(pages)} pages in space {space_key}")
                    
                    # Process pages in batches
                    batch_size = 10
                    for i in range(0, len(pages), batch_size):
                        batch = pages[i:i + batch_size]
                        documents = []
                        
                        # Process each page in the batch
                        for page in batch:
                            try:
                                # Get full page content if not already expanded
                                if 'body' not in page or 'storage' not in page.get('body', {}):
                                    page = self.confluence_client.get_page_content(page['id'])
                                    if not page:
                                        continue
                                
                                # Process page into documents
                                page_docs = DataProcessor.process_confluence_page(page)
                                documents.extend(page_docs)
                                
                            except Exception as e:
                                logger.error(f"Failed to process page {page.get('id', 'unknown')}: {e}")
                                continue
                        
                        # Add batch to vector database
                        if documents:
                            # Delete existing documents first (for updates)
                            if self.incremental_sync:
                                existing_ids = [doc['id'] for doc in documents]
                                await delete_documents(existing_ids)
                            
                            # Add new documents
                            added_count = await add_documents_batch(documents)
                            total_processed += added_count
                            
                            logger.info(f"Added {added_count} documents from batch")
                        
                        # Small delay between batches
                        time.sleep(1)
                
                except Exception as e:
                    logger.error(f"Failed to process space {space_key}: {e}")
                    continue
            
            logger.info(f"Confluence sync completed. Processed {total_processed} documents")
            return total_processed
            
        except Exception as e:
            logger.error(f"Confluence sync failed: {e}")
            return 0
    
    async def sync_jira_data(self) -> int:
        """Sync Jira issues to vector database"""
        if not self.jira_client:
            logger.warning("Jira client not initialized, skipping sync")
            return 0
        
        total_processed = 0
        
        try:
            # Determine which projects to sync
            if self.jira_projects:
                # Sync specific projects
                logger.info(f"Syncing specific Jira projects: {self.jira_projects}")
                all_issues = []
                for project_key in self.jira_projects:
                    issues = self.jira_client.get_resolved_issues(
                        project_key=project_key,
                        days=self.sync_days if self.incremental_sync else 365,  # Last year for full sync
                        limit=500
                    )
                    all_issues.extend(issues)
                    logger.info(f"Found {len(issues)} resolved issues in project {project_key}")
            else:
                # Sync all projects
                logger.info("Syncing all Jira projects")
                all_issues = self.jira_client.get_resolved_issues(
                    days=self.sync_days if self.incremental_sync else 365,  # Last year for full sync
                    limit=500
                )
                logger.info(f"Found {len(all_issues)} resolved Jira issues")
            
            issues = all_issues
            
            # Process issues in batches
            batch_size = 20
            for i in range(0, len(issues), batch_size):
                batch = issues[i:i + batch_size]
                documents = []
                
                # Process each issue in the batch
                for issue in batch:
                    try:
                        issue_docs = DataProcessor.process_jira_issue(issue)
                        documents.extend(issue_docs)
                    except Exception as e:
                        logger.error(f"Failed to process issue {issue.get('key', 'unknown')}: {e}")
                        continue
                
                # Add batch to vector database
                if documents:
                    # Delete existing documents first (for updates)
                    if self.incremental_sync:
                        existing_ids = [doc['id'] for doc in documents]
                        await delete_documents(existing_ids)
                    
                    # Add new documents
                    added_count = await add_documents_batch(documents)
                    total_processed += added_count
                    
                    logger.info(f"Added {added_count} documents from Jira batch")
                
                # Small delay between batches
                time.sleep(1)
            
            logger.info(f"Jira sync completed. Processed {total_processed} documents")
            return total_processed
            
        except Exception as e:
            logger.error(f"Jira sync failed: {e}")
            return 0
    
    async def cleanup_old_documents(self):
        """Clean up old or orphaned documents (optional)"""
        try:
            # This is a placeholder for cleanup logic
            # In a production system, you might want to:
            # 1. Identify documents that no longer exist in source systems
            # 2. Remove duplicate documents
            # 3. Clean up failed partial syncs
            
            stats = await get_collection_stats()
            logger.info(f"Collection stats after sync: {stats}")
            
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
    
    async def run_sync(self) -> Dict[str, Any]:
        """Run the complete synchronization process"""
        start_time = time.time()
        results = {
            'start_time': start_time,
            'confluence_count': 0,
            'jira_count': 0,
            'total_count': 0,
            'success': False,
            'errors': []
        }
        
        try:
            logger.info("Starting data synchronization...")
            
            # Check RAG system health
            if not await rag_health_check():
                raise Exception("RAG system health check failed")
            
            # Sync Confluence data
            if self.sync_confluence:
                try:
                    confluence_count = await self.sync_confluence_data()
                    results['confluence_count'] = confluence_count
                    logger.info(f"Confluence sync completed: {confluence_count} documents")
                except Exception as e:
                    error_msg = f"Confluence sync failed: {e}"
                    logger.error(error_msg)
                    results['errors'].append(error_msg)
            
            # Sync Jira data
            if self.sync_jira:
                try:
                    jira_count = await self.sync_jira_data()
                    results['jira_count'] = jira_count
                    logger.info(f"Jira sync completed: {jira_count} documents")
                except Exception as e:
                    error_msg = f"Jira sync failed: {e}"
                    logger.error(error_msg)
                    results['errors'].append(error_msg)
            
            # Cleanup
            await self.cleanup_old_documents()
            
            # Calculate totals
            results['total_count'] = results['confluence_count'] + results['jira_count']
            results['success'] = results['total_count'] > 0 or len(results['errors']) == 0
            
            end_time = time.time()
            duration = end_time - start_time
            
            logger.info(f"Sync completed in {duration:.2f}s. Total documents: {results['total_count']}")
            
            return results
            
        except Exception as e:
            error_msg = f"Sync process failed: {e}"
            logger.error(error_msg)
            results['errors'].append(error_msg)
            results['success'] = False
            return results

def main():
    """Main entry point for the sync job"""
    logger.info("🚀 Starting data synchronization job")
    
    try:
        # Create and run sync manager
        sync_manager = SyncManager()
        results = asyncio.run(sync_manager.run_sync())
        
        # Log results
        if results['success']:
            logger.info("✅ Sync job completed successfully")
            logger.info(f"📊 Results: Confluence={results['confluence_count']}, "
                       f"Jira={results['jira_count']}, Total={results['total_count']}")
        else:
            logger.error("❌ Sync job completed with errors")
            for error in results['errors']:
                logger.error(f"  - {error}")
        
        # Exit with appropriate code
        exit_code = 0 if results['success'] else 1
        
        if results['total_count'] == 0 and results['success']:
            logger.warning("⚠️  No documents were processed (this might be expected for incremental sync)")
        
        sys.exit(exit_code)
        
    except Exception as e:
        logger.error(f"💥 Sync job failed with exception: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()