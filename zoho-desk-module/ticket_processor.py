import logging
import re
from typing import List, Dict, Any
from datetime import datetime
from bs4 import BeautifulSoup
import html

logger = logging.getLogger(__name__)

class TicketProcessor:
    """Processes Zoho Desk tickets and conversations for RAG ingestion"""
    
    @staticmethod
    def clean_html_content(html_content: str) -> str:
        """Clean HTML content and extract text"""
        if not html_content:
            return ""
        
        try:
            # Parse HTML
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style", "nav", "header", "footer"]):
                script.decompose()
            
            # Get text content
            text = soup.get_text()
            
            # Clean up whitespace
            text = re.sub(r'\n\s*\n', '\n\n', text)  # Multiple newlines to double
            text = re.sub(r' +', ' ', text)          # Multiple spaces to single
            text = text.strip()
            
            # Decode HTML entities
            text = html.unescape(text)
            
            return text
            
        except Exception as e:
            logger.error(f"Failed to clean HTML content: {e}")
            return html_content  # Return original if cleaning fails
    
    @staticmethod
    def chunk_text(text: str, max_chunk_size: int = 1000, overlap: int = 100) -> List[str]:
        """Split text into overlapping chunks for better retrieval"""
        if len(text) <= max_chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + max_chunk_size
            
            # Try to break at paragraph boundary
            if end < len(text):
                paragraph_end = text.rfind('\n\n', start, end)
                if paragraph_end != -1 and paragraph_end > start + max_chunk_size // 2:
                    end = paragraph_end + 2
                else:
                    # Try to break at sentence boundary
                    sentence_end = text.rfind('.', start, end)
                    if sentence_end != -1 and sentence_end > start + max_chunk_size // 2:
                        end = sentence_end + 1
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            # Move start position with overlap
            start = end - overlap
            if start >= len(text):
                break
        
        return chunks
    
    @staticmethod
    def extract_ticket_content(ticket: Dict[str, Any], conversations: List[Dict[str, Any]]) -> str:
        """Extract and combine all text content from ticket and conversations"""
        content_parts = []
        
        # Add ticket subject and description
        if ticket.get('subject'):
            content_parts.append(f"Subject: {ticket['subject']}")
        
        if ticket.get('description'):
            clean_description = TicketProcessor.clean_html_content(ticket['description'])
            if clean_description:
                content_parts.append(f"Description: {clean_description}")
        
        # Add conversations in chronological order
        if conversations:
            # Sort conversations by created time
            sorted_conversations = sorted(
                conversations, 
                key=lambda x: x.get('createdTime', ''),
                reverse=False
            )
            
            content_parts.append("Conversation History:")
            
            for conv in sorted_conversations:
                # Skip if it's a system message or has no content
                if conv.get('direction') == 'in' or conv.get('content'):
                    author = conv.get('author', {}).get('name', 'Unknown')
                    content = TicketProcessor.clean_html_content(conv.get('content', ''))
                    
                    if content:
                        timestamp = conv.get('createdTime', '')
                        content_parts.append(f"\n[{author} - {timestamp}]: {content}")
        
        return "\n\n".join(content_parts)
    
    @staticmethod
    def process_ticket(ticket: Dict[str, Any], 
                      conversations: List[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Process a Zoho Desk ticket into documents for vector storage"""
        try:
            ticket_id = ticket.get('id')
            subject = ticket.get('subject', 'No Subject')
            
            # Extract all content
            full_content = TicketProcessor.extract_ticket_content(ticket, conversations or [])
            
            if len(full_content) < 50:  # Skip very short tickets
                logger.debug(f"Skipping short ticket {ticket_id}: {subject}")
                return []
            
            # Create chunks
            chunks = TicketProcessor.chunk_text(full_content)
            
            # Create documents for each chunk
            documents = []
            
            # Extract metadata
            department = ticket.get('departmentId', 'unknown')
            status = ticket.get('status', 'unknown')
            priority = ticket.get('priority', 'unknown')
            category = ticket.get('category', 'unknown')
            assignee = ticket.get('assignee', {})
            contact = ticket.get('contact', {})
            
            # Build ticket URL (format may vary by domain)
            ticket_url = f"https://desk.zoho.com/agent/tickets/{ticket_id}"
            
            for i, chunk in enumerate(chunks):
                doc_id = f"zoho_ticket_{ticket_id}_{i}" if len(chunks) > 1 else f"zoho_ticket_{ticket_id}"
                
                documents.append({
                    'id': doc_id,
                    'content': chunk,
                    'metadata': {
                        'type': 'zoho_desk_ticket',
                        'source_id': ticket_id,
                        'title': subject,
                        'department_id': department,
                        'status': status,
                        'priority': priority,
                        'category': category,
                        'assignee_name': assignee.get('name', 'Unassigned'),
                        'assignee_email': assignee.get('emailId', ''),
                        'contact_name': contact.get('name', 'Unknown'),
                        'contact_email': contact.get('email', ''),
                        'url': ticket_url,
                        'created_time': ticket.get('createdTime'),
                        'modified_time': ticket.get('modifiedTime'),
                        'closed_time': ticket.get('closedTime'),
                        'conversation_count': len(conversations) if conversations else 0,
                        'chunk_index': i,
                        'total_chunks': len(chunks)
                    }
                })
            
            logger.debug(f"Processed ticket {subject} into {len(documents)} chunks")
            return documents
            
        except Exception as e:
            logger.error(f"Failed to process ticket {ticket.get('id', 'unknown')}: {e}")
            return []
    
    @staticmethod
    def process_ticket_batch(tickets_with_conversations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process a batch of tickets with their conversations"""
        all_documents = []
        
        for item in tickets_with_conversations:
            ticket = item.get('ticket', {})
            conversations = item.get('conversations', [])
            
            try:
                documents = TicketProcessor.process_ticket(ticket, conversations)
                all_documents.extend(documents)
            except Exception as e:
                logger.error(f"Failed to process ticket in batch: {e}")
                continue
        
        logger.info(f"Processed batch of {len(tickets_with_conversations)} tickets into {len(all_documents)} documents")
        return all_documents
    
    @staticmethod
    def filter_relevant_tickets(tickets: List[Dict[str, Any]], 
                               min_conversations: int = 2,
                               required_status: List[str] = None) -> List[Dict[str, Any]]:
        """Filter tickets that are most valuable for knowledge base"""
        if required_status is None:
            required_status = ['Closed', 'Resolved']
        
        relevant_tickets = []
        
        for ticket in tickets:
            # Check status
            if ticket.get('status') not in required_status:
                continue
            
            # Check if it has enough content to be valuable
            description = ticket.get('description', '')
            subject = ticket.get('subject', '')
            
            if len(description) < 50 and len(subject) < 20:
                continue
            
            # Prefer tickets with resolutions or solutions
            if any(keyword in description.lower() for keyword in ['solution', 'resolved', 'fixed', 'answer']):
                relevant_tickets.append(ticket)
                continue
            
            # Include tickets with multiple interactions (likely more valuable)
            # Note: We'll check conversation count when we have that data
            relevant_tickets.append(ticket)
        
        logger.info(f"Filtered {len(tickets)} tickets to {len(relevant_tickets)} relevant tickets")
        return relevant_tickets
