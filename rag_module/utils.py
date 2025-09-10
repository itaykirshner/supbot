import re
import html
from typing import List
from bs4 import BeautifulSoup

def clean_text(text: str) -> str:
    """Clean and normalize text content"""
    if not text:
        return ""
    
    # Parse HTML content
    soup = BeautifulSoup(text, 'html.parser')
    
    # Remove script and style elements
    for script in soup(["script", "style"]):
        script.decompose()
    
    # Get text content
    text = soup.get_text()
    
    # Clean up whitespace
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    
    # Decode HTML entities
    text = html.unescape(text)
    
    return text

def chunk_text(text: str, max_chunk_size: int = 1000, overlap: int = 100) -> List[str]:
    """Split text into overlapping chunks"""
    if len(text) <= max_chunk_size:
        return [text]
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + max_chunk_size
        
        # Try to break at sentence boundary
        if end < len(text):
            # Look for sentence endings within the last 200 characters
            sentence_end = text.rfind('.', end - 200, end)
            if sentence_end != -1:
                end = sentence_end + 1
        
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        
        # Move start position with overlap
        start = end - overlap
        if start >= len(text):
            break
    
    return chunks

def format_confluence_content(page_data: dict) -> dict:
    """Format Confluence page data for storage"""
    title = page_data.get('title', 'Untitled')
    content = page_data.get('body', {}).get('storage', {}).get('value', '')
    
    # Clean the content
    cleaned_content = clean_text(content)
    
    # Create chunks
    chunks = chunk_text(cleaned_content)
    
    return {
        'title': title,
        'content': cleaned_content,
        'chunks': chunks,
        'metadata': {
            'id': page_data.get('id'),
            'title': title,
            'type': 'confluence',
            'space': page_data.get('space', {}).get('key', 'unknown'),
            'url': page_data.get('_links', {}).get('webui', ''),
            'created': page_data.get('createdDate'),
            'modified': page_data.get('lastModified')
        }
    }

