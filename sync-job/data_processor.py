import logging
import re
from typing import List, Dict, Any
from bs4 import BeautifulSoup
import html

logger = logging.getLogger(__name__)

class DataProcessor:
    """Processes and formats data for ingestion into vector database"""
    
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
    def process_confluence_page(page: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process a Confluence page into chunks for vector storage"""
        try:
            page_id = page.get('id')
            title = page.get('title', 'Untitled')
            
            # Extract content
            body = page.get('body', {})
            storage = body.get('storage', {})
            html_content = storage.get('value', '')
            
            if not html_content:
                logger.warning(f"No content found for page {page_id}")
                return []
            
            # Clean HTML content
            clean_content = DataProcessor.clean_html_content(html_content)
            
            if len(clean_content) < 50:  # Skip very short pages
                logger.debug(f"Skipping short page {page_id}: {title}")
                return []
            
            # Create chunks
            chunks = DataProcessor.chunk_text(clean_content)
            
            # Create documents for each chunk
            documents = []
            space_info = page.get('space', {})
            version_info = page.get('version', {})
            
            base_url = page.get('_links', {}).get('base', '')
            web_ui = page.get('_links', {}).get('webui', '')
            full_url = f"{base_url}{web_ui}" if base_url and web_ui else web_ui
            
            for i, chunk in enumerate(chunks):
                doc_id = f"conf_{page_id}_{i}" if len(chunks) > 1 else f"conf_{page_id}"
                
                documents.append({
                    'id': doc_id,
                    'content': chunk,
                    'metadata': {
                        'type': 'confluence',
                        'source_id': page_id,
                        'title': title,
                        'space_key': space_info.get('key', 'unknown'),
                        'space_name': space_info.get('name', 'Unknown Space'),
                        'url': full_url,
                        'created_date': version_info.get('when'),
                        'version': version_info.get('number'),
                        'chunk_index': i,
                        'total_chunks': len(chunks)
                    }
                })
            
            logger.debug(f"Processed page {title} into {len(documents)} chunks")
            return documents
            
        except Exception as e:
            logger.error(f"Failed to process Confluence page {page.get('id', 'unknown')}: {e}")
            return []
    
    @staticmethod
    def process_jira_issue(issue: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process a Jira issue into documents for vector storage"""
        try:
            issue_key = issue.get('key')
            fields = issue.get('fields', {})
            
            summary = fields.get('summary', 'No Summary')
            description = fields.get('description', '')
            
            if not description:
                logger.debug(f"Skipping Jira issue {issue_key} with no description")
                return []
            
            # Clean description (might be HTML in some cases)
            clean_description = DataProcessor.clean_html_content(description)
            
            # Combine summary and description
            full_content = f"{summary}\n\n{clean_description}"
            
            if len(full_content) < 50:
                logger.debug(f"Skipping short Jira issue {issue_key}")
                return []
            
            # Create chunks if content is long
            chunks = DataProcessor.chunk_text(full_content)
            
            documents = []
            project = fields.get('project', {})
            issue_type = fields.get('issuetype', {})
            status = fields.get('status', {})
            resolution = fields.get('resolution', {})
            
            for i, chunk in enumerate(chunks):
                doc_id = f"jira_{issue_key}_{i}" if len(chunks) > 1 else f"jira_{issue_key}"
                
                documents.append({
                    'id': doc_id,
                    'content': chunk,
                    'metadata': {
                        'type': 'jira',
                        'source_id': issue_key,
                        'title': summary,
                        'project_key': project.get('key', 'unknown'),
                        'project_name': project.get('name', 'Unknown Project'),
                        'issue_type': issue_type.get('name', 'Unknown'),
                        'status': status.get('name', 'Unknown'),
                        'resolution': resolution.get('name', 'Unresolved') if resolution else 'Unresolved',
                        'url': f"{issue.get('self', '').replace('/rest/api/2/issue/', '/browse/')}" if issue.get('self') else '',
                        'created': fields.get('created'),
                        'resolved': fields.get('resolutiondate'),
                        'chunk_index': i,
                        'total_chunks': len(chunks)
                    }
                })
            
            logger.debug(f"Processed Jira issue {issue_key} into {len(documents)} chunks")
            return documents
            
        except Exception as e:
            logger.error(f"Failed to process Jira issue {issue.get('key', 'unknown')}: {e}")
            return []
