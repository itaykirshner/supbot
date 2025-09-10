import logging
import os
import sys
import time
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime, timedelta

# Add modules to path
sys.path.append(str(Path(__file__).parent.parent / "rag-module"))
sys.path.append(str(Path(__file__).parent.parent / "zoho-desk-module"))

from rag_client import RAGClient
from zoho_desk_client import ZohoDeskClient
from zoho_auth import ZohoDeskAuth
from ticket_processor import TicketProcessor

logger = logging.getLogger(__name__)

class ZohoDeskSyncManager:
    """Manages synchronization of Zoho Desk data to vector database"""
    
    def __init__(self):
        # Configuration
        self.sync_enabled = os.environ.get("SYNC_ZOHO_DESK", "false").lower() == "true"
        self.sync_days = int(os.environ.get("ZOHO_SYNC_DAYS", "30"))  # Default 30 days
        self.incremental_sync = os.environ.get("ZOHO_INCREMENTAL_SYNC", "true").lower() == "true"
        self.max_tickets = int(os.environ.get("ZOHO_MAX_TICKETS", "500"))
        self.include_conversations = os.environ.get("ZOHO_INCLUDE_CONVERSATIONS", "true").lower() == "true"
        
        # Filters
        self.department_ids = self._parse_list(os.environ.get("ZOHO_DEPARTMENT_IDS", ""))
        self.ticket_statuses = self._parse_list(os.environ.get("ZOHO_TICKET_STATUSES", "Closed,Resolved"))
        
        logger.info(f"Zoho Desk sync configuration:")
        logger.info(f"  Enabled: {self.sync_enabled}")
        logger.info(f"  Incremental: {self.incremental_sync}")
        logger.info(f"  Sync days: {self.sync_days}")
        logger.info(f"  Max tickets: {self.max_tickets}")
        logger.info(f"  Include conversations: {self.include_conversations}")
        logger.info(f"  Department filter: {self.department_ids}")
        logger.info(f"  Status filter: {self.ticket_statuses}")
        
        # Initialize clients
        self.rag_client = None
        self.zoho_client = None
        
        if self.sync_enabled:
            self._initialize_clients()
    
    def _parse_list(self, list_string: str) -> List[str]:
        """Parse comma-separated list"""
        if not list_string:
            return []
        return [item.strip() for item in list_string.split(",") if item.strip()]
    
    def _initialize_clients(self):
        """Initialize required clients"""
        try:
            # Initialize RAG client
            self.rag_client = RAGClient()
            logger.info("RAG client initialized for Zoho Desk sync")
            
            # Initialize Zoho Desk client
            auth = ZohoDeskAuth()
            self.zoho_client = ZohoDeskClient(auth=auth)
            
            # Test connection
            if not self.zoho_client.test_connection():
                raise Exception("Zoho Desk connection test failed")
            
            logger.info("Zoho Desk client initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Zoho Desk sync clients: {e}")
            raise
    
    def get_tickets_to_sync(self) -> List[Dict[str, Any]]:
        """Get tickets that should be synced based on configuration"""
        if not self.zoho_client:
            return []
        
        try:
            tickets = []
            
            if self.incremental_sync:
                logger.info("Performing incremental sync of recently updated tickets")
                tickets = self.zoho_client.get_recently_updated_tickets(
                    days=self.sync_days,
                    limit=self.max_tickets
                )
            else:
                logger.info("Performing full sync of resolved tickets")
                tickets = self.zoho_client.get_resolved_tickets(
                    days=self.sync_days,
                    limit=self.max_tickets
                )
            
            # Apply filters
            filtered_tickets = self._filter_tickets(tickets)
            
            logger.info(f"Retrieved {len(tickets)} tickets, {len(filtered_tickets)} after filtering")
            return filtered_tickets
            
        except Exception as e:
            logger.error(f"Failed to get tickets to sync: {e}")
            return []
    
    def _filter_tickets(self, tickets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply filters to tickets"""
        filtered = []
        
        for ticket in tickets:
            # Filter by department if specified
            if self.department_ids:
                dept_id = str(ticket.get('departmentId', ''))
                if dept_id not in self.department_ids:
                    continue
            
            # Filter by status if specified
            if self.ticket_statuses:
                status = ticket.get('status', '')
                if status not in self.ticket_statuses:
                    continue
            
            # Use processor to check if ticket is valuable
            if len(ticket.get('subject', '') + ticket.get('description', '')) < 50:
                continue
            
            filtered.append(ticket)
        
        return filtered
    
    def get_ticket_conversations(self, ticket_id: str) -> List[Dict[str, Any]]:
        """Get conversations for a ticket if enabled"""
        if not self.include_conversations or not self.zoho_client:
            return []
        
        try:
            return self.zoho_client.get_ticket_conversations(ticket_id)
        except Exception as e:
            logger.error(f"Failed to get conversations for ticket {ticket_id}: {e}")
            return []
    
    def sync_tickets_batch(self, tickets: List[Dict[str, Any]]) -> int:
        """Sync a batch of tickets with their conversations"""
        if not tickets or not self.rag_client:
            return 0
        
        processed_count = 0
        
        try:
            # Prepare tickets with conversations
            tickets_with_conversations = []
            
            for ticket in tickets:
                ticket_id = ticket.get('id')
                conversations = self.get_ticket_conversations(ticket_id)
                
                tickets_with_conversations.append({
                    'ticket': ticket,
                    'conversations': conversations
                })
                
                # Small delay to respect API limits
                time.sleep(0.1)
            
            # Process tickets into documents
            documents = TicketProcessor.process_ticket_batch(tickets_with_conversations)
            
            if documents:
                # Delete existing documents for incremental sync
                if self.incremental_sync:
                    existing_ids = [doc['id'] for doc in documents]
                    self.rag_client.delete_documents(existing_ids)
                
                # Add new documents
                added_count = self.rag_client.add_documents_batch(documents)
                processed_count = added_count
                
                logger.info(f"Added {added_count} Zoho Desk documents to knowledge base")
            
            return processed_count
            
        except Exception as e:
            logger.error(f"Failed to sync tickets batch: {e}")
            return 0
    
    def sync_zoho_desk_data(self) -> int:
        """Sync Zoho Desk tickets to vector database"""
        if not self.sync_enabled:
            logger.info("Zoho Desk sync is disabled")
            return 0
        
        total_processed = 0
        start_time = time.time()
        
        try:
            logger.info("Starting Zoho Desk data synchronization...")
            
            # Get tickets to sync
            tickets = self.get_tickets_to_sync()
            
            if not tickets:
                logger.info("No tickets found to sync")
                return 0
            
            # Process tickets in batches
            batch_size = 10  # Smaller batches due to conversation API calls
            
            for i in range(0, len(tickets), batch_size):
                batch = tickets[i:i + batch_size]
                
                logger.info(f"Processing batch {i//batch_size + 1} of {(len(tickets) + batch_size - 1)//batch_size}")
                
                try:
                    batch_count = self.sync_tickets_batch(batch)
                    total_processed += batch_count
                    
                    logger.info(f"Batch processed: {batch_count} documents added")
                    
                except Exception as e:
                    logger.error(f"Failed to process batch {i//batch_size + 1}: {e}")
                    continue
                
                # Delay between batches to respect API limits
                time.sleep(2)
            
            duration = time.time() - start_time
            logger.info(f"Zoho Desk sync completed in {duration:.2f}s. Processed {total_processed} documents")
            
            return total_processed
            
        except Exception as e:
            logger.error(f"Zoho Desk sync failed: {e}")
            return 0
    
    def get_sync_statistics(self) -> Dict[str, Any]:
        """Get statistics about Zoho Desk data in vector database"""
        try:
            if not self.rag_client:
                return {}
            
            # This would require a way to query by metadata type
            # Implementation depends on your RAG client capabilities
            stats = {
                'sync_enabled': self.sync_enabled,
                'last_sync_time': datetime.now().isoformat(),
                'configuration': {
                    'sync_days': self.sync_days,
                    'incremental_sync': self.incremental_sync,
                    'max_tickets': self.max_tickets,
                    'include_conversations': self.include_conversations,
                    'department_filter': self.department_ids,
                    'status_filter': self.ticket_statuses
                }
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get sync statistics: {e}")
            return {}
