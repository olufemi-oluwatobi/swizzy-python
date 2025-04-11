"""
Tools for web content extraction and search.
"""
import os
import logging
import json
from typing import Dict, List, Any, Optional
from app.services.jina_service import JinaService
from app.services.serp_service import SerpService
from agents import function_tool

logger = logging.getLogger(__name__)

@function_tool
def read_url(url: str, extract_type: str = "full") -> str:
    """
    Reads content from a URL using Jina API.
    
    Args:
        url: The URL to read
        extract_type: Type of extraction - 'full' for complete HTML, 'article' for main article content
        
    Returns:
        The extracted content in a readable format
    """
    logger.info(f"Reading URL: {url} with extraction type: {extract_type}")
    
    try:
        # Initialize Jina service
        jina_service = JinaService()
        
        # Extract content based on type
        if extract_type == "article":
            result = jina_service.extract_article(url)
            
            if result.get("success"):
                # Return markdown format for article
                return result["markdown"]
            else:
                error_message = result.get("error", "Unknown error")
                logger.error(f"Error extracting article from URL: {error_message}")
                return f"Error extracting article from URL: {error_message}"
        else:
            # Full content extraction
            result = jina_service.read_url(url)
            
            if result.get("success"):
                # Return main text with metadata
                metadata = result["metadata"]
                main_text = result.get("main_text", "No main text extracted")
                
                output = f"# {metadata.get('title', 'No Title')}\n\n"
                output += f"URL: {url}\n\n"
                output += f"## Content\n\n{main_text}\n\n"
                
                return output
            else:
                error_message = result.get("error", "Unknown error")
                logger.error(f"Error reading URL: {error_message}")
                return f"Error reading URL: {error_message}"
            
    except Exception as e:
        logger.exception(f"Error reading URL {url}: {e}")
        return f"Error reading URL: {e}"

@function_tool
def extract_url_to_markdown(url: str) -> str:
    """
    Extracts content from a URL and converts it to a well-formatted Markdown document.
    
    Args:
        url: The URL to extract content from
        
    Returns:
        Markdown content as a string
    """
    logger.info(f"Extracting URL to Markdown: {url}")
    
    try:
        # Use the article extraction mode for better formatting
        return read_url(url, extract_type="article")
            
    except Exception as e:
        logger.exception(f"Error extracting URL to Markdown {url}: {e}")
        return f"Error extracting URL to Markdown: {e}"

@function_tool
def search_web(query: str, num_results: int = 5, search_type: str = "web") -> str:
    """
    Searches the web using Google Search API.
    
    Args:
        query: The search query
        num_results: Number of results to return (max 10)
        search_type: Type of search - 'web', 'image', or 'news'
        
    Returns:
        Search results in a readable format
    """
    logger.info(f"Searching web for: {query} with type: {search_type}")
    
    try:
        # Initialize SERP service
        serp_service = SerpService()
        
        # Perform search
        result = serp_service.search(query, num_results, search_type)
        
        if result.get("success"):
            # Format results as markdown
            output = f"# Search Results for: {query}\n\n"
            
            if search_type == "image":
                output += "## Image Results\n\n"
                for i, item in enumerate(result["results"]):
                    output += f"{i+1}. [{item['title']}]({item['link']})\n"
                    output += f"   ![{item['title']}]({item['imageUrl']})\n\n"
            else:
                output += "## Web Results\n\n"
                for i, item in enumerate(result["results"]):
                    output += f"{i+1}. [{item['title']}]({item['link']})\n"
                    output += f"   {item['snippet']}\n"
                    output += f"   Source: {item['displayLink']}\n\n"
            
            # Add search metadata
            output += f"\n---\n"
            output += f"Total results: {result['total_results']}\n"
            output += f"Search time: {result['search_time']} seconds\n"
            output += f"Cost: ${result['cost']:.4f}\n"
            
            return output
        else:
            error_message = result.get("error", "Unknown error")
            logger.error(f"Error searching web: {error_message}")
            return f"Error searching web: {error_message}"
            
    except Exception as e:
        logger.exception(f"Error searching web for {query}: {e}")
        return f"Error searching web: {e}"

@function_tool
def search_with_budget(query: str, budget: float, num_results: int = 5, search_type: str = "web") -> str:
    """
    Searches the web with a specified budget limit.
    
    Args:
        query: The search query
        budget: Maximum budget in dollars
        num_results: Number of results to return (max 10)
        search_type: Type of search - 'web', 'image', or 'news'
        
    Returns:
        Search results in a readable format
    """
    logger.info(f"Searching web with budget ${budget} for: {query}")
    
    try:
        # Initialize SERP service
        serp_service = SerpService()
        
        # Perform search with budget
        result = serp_service.search_with_budget(query, budget, num_results, search_type)
        
        if result.get("success"):
            # Format results as markdown
            output = f"# Search Results for: {query}\n\n"
            
            if search_type == "image":
                output += "## Image Results\n\n"
                for i, item in enumerate(result["results"]):
                    output += f"{i+1}. [{item['title']}]({item['link']})\n"
                    output += f"   ![{item['title']}]({item['imageUrl']})\n\n"
            else:
                output += "## Web Results\n\n"
                for i, item in enumerate(result["results"]):
                    output += f"{i+1}. [{item['title']}]({item['link']})\n"
                    output += f"   {item['snippet']}\n"
                    output += f"   Source: {item['displayLink']}\n\n"
            
            # Add search metadata
            output += f"\n---\n"
            output += f"Total results: {result['total_results']}\n"
            output += f"Search time: {result['search_time']} seconds\n"
            output += f"Cost: ${result['cost']:.4f}\n"
            output += f"Total cost: ${result['total_cost']:.4f}\n"
            output += f"Budget remaining: ${budget - result['total_cost']:.4f}\n"
            
            return output
        else:
            error_message = result.get("error", "Unknown error")
            logger.error(f"Error searching web: {error_message}")
            return f"Error searching web: {error_message}"
            
    except Exception as e:
        logger.exception(f"Error searching web for {query}: {e}")
        return f"Error searching web: {e}"

@function_tool
def reset_search_budget() -> str:
    """
    Resets the search cost tracking.
    
    Returns:
        Confirmation message
    """
    logger.info("Resetting search budget tracking")
    
    try:
        # Initialize SERP service
        serp_service = SerpService()
        
        # Reset cost tracking
        serp_service.reset_cost_tracking()
        
        return "Search budget tracking has been reset."
            
    except Exception as e:
        logger.exception(f"Error resetting search budget: {e}")
        return f"Error resetting search budget: {e}"

@function_tool
def get_search_cost_summary() -> str:
    """
    Gets a summary of the current search costs.
    
    Returns:
        Cost summary in a readable format
    """
    logger.info("Getting search cost summary")
    
    try:
        # Initialize SERP service
        serp_service = SerpService()
        
        # Get cost summary
        summary = serp_service.get_cost_summary()
        
        # Format as markdown
        output = "# Search Cost Summary\n\n"
        output += f"Cost per query: ${summary['cost_per_query']:.4f}\n"
        output += f"Total cost: ${summary['total_cost']:.4f}\n"
        output += f"Queries performed: {summary['queries_performed']}\n"
        
        return output
            
    except Exception as e:
        logger.exception(f"Error getting search cost summary: {e}")
        return f"Error getting search cost summary: {e}"
