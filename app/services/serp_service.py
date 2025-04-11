"""
Service for web search using Google Search API.
"""
import os
import logging
import requests
from typing import Dict, List, Any, Optional
import json
import time

logger = logging.getLogger(__name__)

class SerpService:
    """Service for web search using Google Search API."""
    
    def __init__(self):
        """Initialize the SERP service."""
        self.api_key = os.environ.get("GOOGLE_SEARCH_API_KEY")
        if not self.api_key:
            logger.warning("GOOGLE_SEARCH_API_KEY environment variable not set. SERP service will not function.")
        
        self.search_engine_id = os.environ.get("GOOGLE_SEARCH_ENGINE_ID")
        if not self.search_engine_id:
            logger.warning("GOOGLE_SEARCH_ENGINE_ID environment variable not set. SERP service will not function.")
        
        self.api_base_url = "https://www.googleapis.com/customsearch/v1"
        self.cost_per_query = 0.005  # Cost in dollars per search query
        self.total_cost = 0.0
    
    def search(self, query: str, num_results: int = 10, search_type: str = "web") -> Dict[str, Any]:
        """
        Perform a web search using Google Search API.
        
        Args:
            query: The search query
            num_results: Number of results to return (max 10)
            search_type: Type of search - 'web', 'image', or 'news'
            
        Returns:
            Dictionary containing the search results
        """
        if not self.api_key or not self.search_engine_id:
            return {"error": "API key or Search Engine ID not set"}
        
        try:
            # Prepare request parameters
            params = {
                "key": self.api_key,
                "cx": self.search_engine_id,
                "q": query,
                "num": min(num_results, 10)  # Google API limits to 10 results per query
            }
            
            # Add search type if specified
            if search_type == "image":
                params["searchType"] = "image"
            elif search_type == "news":
                params["sort"] = "date"  # Sort by date for news
            
            # Make API request
            response = requests.get(self.api_base_url, params=params)
            response.raise_for_status()
            
            # Parse response
            result = response.json()
            
            # Update cost tracking
            self.total_cost += self.cost_per_query
            
            # Format results
            formatted_results = []
            if "items" in result:
                for item in result["items"]:
                    formatted_item = {
                        "title": item.get("title", ""),
                        "link": item.get("link", ""),
                        "snippet": item.get("snippet", ""),
                        "displayLink": item.get("displayLink", "")
                    }
                    
                    # Add image-specific fields
                    if search_type == "image" and "image" in item:
                        formatted_item["imageUrl"] = item["image"].get("thumbnailLink", "")
                        formatted_item["imageHeight"] = item["image"].get("height", 0)
                        formatted_item["imageWidth"] = item["image"].get("width", 0)
                    
                    formatted_results.append(formatted_item)
            
            return {
                "success": True,
                "query": query,
                "results": formatted_results,
                "total_results": result.get("searchInformation", {}).get("totalResults", "0"),
                "search_time": result.get("searchInformation", {}).get("searchTime", 0),
                "cost": self.cost_per_query,
                "total_cost": self.total_cost
            }
                
        except Exception as e:
            logger.exception(f"Error performing search: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def search_with_budget(self, query: str, budget: float, num_results: int = 10, search_type: str = "web") -> Dict[str, Any]:
        """
        Perform a web search with a specified budget limit.
        
        Args:
            query: The search query
            budget: Maximum budget in dollars
            num_results: Number of results to return (max 10)
            search_type: Type of search - 'web', 'image', or 'news'
            
        Returns:
            Dictionary containing the search results
        """
        # Check if search would exceed budget
        if self.total_cost + self.cost_per_query > budget:
            return {
                "success": False,
                "error": f"Search would exceed budget. Current cost: ${self.total_cost}, Budget: ${budget}",
                "budget_remaining": budget - self.total_cost
            }
        
        # Perform search
        return self.search(query, num_results, search_type)
    
    def reset_cost_tracking(self) -> None:
        """Reset the cost tracking."""
        self.total_cost = 0.0
    
    def get_cost_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the current costs.
        
        Returns:
            Dictionary containing cost information
        """
        return {
            "cost_per_query": self.cost_per_query,
            "total_cost": self.total_cost,
            "queries_performed": int(self.total_cost / self.cost_per_query) if self.cost_per_query > 0 else 0
        }
