"""
Service for interacting with Jina API for URL content extraction.
"""
import os
import logging
import requests
from typing import Dict, Any, Optional
from bs4 import BeautifulSoup
import json

logger = logging.getLogger(__name__)

class JinaService:
    """Service for extracting content from URLs using Jina API."""
    
    def __init__(self):
        """Initialize the Jina service."""
        self.api_key = os.environ.get("JINA_API_KEY")
        if not self.api_key:
            logger.warning("JINA_API_KEY environment variable not set. Jina service will not function.")
        
        self.api_base_url = "https://r.jina.ai"
    
    def read_url(self, url: str) -> Dict[str, Any]:
        """
        Read content from a URL using Jina API.
        
        Args:
            url: The URL to read
            
        Returns:
            Dictionary containing the content and metadata
        """
        if not self.api_key:
            return {"error": "JINA_API_KEY not set"}
        
        try:
            # Prepare request
            headers = {
                "Authorization": f"Bearer {self.api_key}"
            }
            
            # Make API request
            full_url = f"{self.api_base_url}/{url}"
            response = requests.get(full_url, headers=headers)
            response.raise_for_status()
            
            # Parse response
            content = response.text
            
            # Extract useful information using BeautifulSoup
            soup = BeautifulSoup(content, 'html.parser')
            
            # Get title
            title = soup.title.string if soup.title else ""
            
            # Get main content (this is a simplified approach)
            # In a real implementation, you might want to use more sophisticated content extraction
            main_content = ""
            for paragraph in soup.find_all('p'):
                main_content += paragraph.get_text() + "\n\n"
            
            # Get metadata
            metadata = {
                "title": title,
                "url": url,
                "content_type": response.headers.get('Content-Type', ''),
                "length": len(content)
            }
            
            return {
                "success": True,
                "content": content,
                "main_text": main_content,
                "metadata": metadata
            }
                
        except Exception as e:
            logger.exception(f"Error reading URL with Jina: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def extract_article(self, url: str) -> Dict[str, Any]:
        """
        Extract article content from a URL, focusing on the main text.
        
        Args:
            url: The URL to extract from
            
        Returns:
            Dictionary containing the article content and metadata
        """
        result = self.read_url(url)
        
        if not result.get("success"):
            return result
        
        try:
            # Parse HTML content
            soup = BeautifulSoup(result["content"], 'html.parser')
            
            # Extract title
            title = soup.title.string if soup.title else ""
            
            # Try to find article content
            article = soup.find('article')
            if article:
                content = article.get_text(separator='\n\n')
            else:
                # Fallback to main content extraction
                content = ""
                main_elements = soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
                for element in main_elements:
                    if len(element.get_text(strip=True)) > 50:  # Filter out short elements
                        content += element.get_text() + "\n\n"
            
            # Extract images
            images = []
            for img in soup.find_all('img'):
                src = img.get('src')
                alt = img.get('alt', '')
                if src:
                    # Handle relative URLs
                    if src.startswith('/'):
                        base_url = '/'.join(url.split('/')[:3])  # Get domain
                        src = base_url + src
                    images.append({
                        "src": src,
                        "alt": alt
                    })
            
            # Extract metadata
            metadata = {
                "title": title,
                "url": url,
                "content_type": "article",
                "word_count": len(content.split()),
                "image_count": len(images)
            }
            
            return {
                "success": True,
                "title": title,
                "content": content,
                "images": images,
                "metadata": metadata,
                "markdown": f"# {title}\n\n{content}\n\nSource: {url}"
            }
                
        except Exception as e:
            logger.exception(f"Error extracting article from URL: {e}")
            return {
                "success": False,
                "error": str(e),
                "original_result": result
            }
