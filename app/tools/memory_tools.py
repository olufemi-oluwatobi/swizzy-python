import os
import logging
import io
import json
import time
from typing import Dict, List, Any, Optional, Union
from app.services import storage_service
from agents import function_tool

logger = logging.getLogger(__name__)

class MemoryStorage:
    """
    A class for storing and retrieving memory items.
    This implementation uses a simple file-based approach for persistence.
    """
    
    def __init__(self, storage_dir: str = "memory_storage"):
        """
        Initialize the memory storage.
        
        Args:
            storage_dir: Directory where memory files will be stored
        """
        self.storage_dir = storage_dir
        self.memory_index = {}
        self.ensure_storage_exists()
        self.load_index()
    
    def ensure_storage_exists(self):
        """Ensure the storage directory exists."""
        os.makedirs(self.storage_dir, exist_ok=True)
    
    def load_index(self):
        """Load the memory index from disk."""
        index_path = os.path.join(self.storage_dir, "memory_index.json")
        if os.path.exists(index_path):
            try:
                with open(index_path, 'r') as f:
                    self.memory_index = json.load(f)
                logger.info(f"Loaded memory index with {len(self.memory_index)} items")
            except Exception as e:
                logger.error(f"Error loading memory index: {e}")
                self.memory_index = {}
        else:
            logger.info("No memory index found, starting with empty index")
            self.memory_index = {}
    
    def save_index(self):
        """Save the memory index to disk."""
        index_path = os.path.join(self.storage_dir, "memory_index.json")
        try:
            with open(index_path, 'w') as f:
                json.dump(self.memory_index, f, indent=2)
            logger.info(f"Saved memory index with {len(self.memory_index)} items")
        except Exception as e:
            logger.error(f"Error saving memory index: {e}")
    
    def store_memory(self, memory_id: str, content: Dict[str, Any]) -> str:
        """
        Store a memory item.
        
        Args:
            memory_id: Unique identifier for the memory
            content: Dictionary containing memory content and metadata
            
        Returns:
            The memory ID
        """
        # Add timestamp if not present
        if "timestamp" not in content:
            content["timestamp"] = time.time()
        
        # Store in index
        self.memory_index[memory_id] = {
            "id": memory_id,
            "title": content.get("title", "Untitled Memory"),
            "tags": content.get("tags", []),
            "timestamp": content["timestamp"],
            "summary": content.get("summary", "")
        }
        
        # Store full content
        memory_path = os.path.join(self.storage_dir, f"{memory_id}.json")
        try:
            with open(memory_path, 'w') as f:
                json.dump(content, f, indent=2)
            logger.info(f"Stored memory with ID: {memory_id}")
            self.save_index()
            return memory_id
        except Exception as e:
            logger.error(f"Error storing memory {memory_id}: {e}")
            return f"Error: {e}"
    
    def retrieve_memory(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a memory item by ID.
        
        Args:
            memory_id: ID of the memory to retrieve
            
        Returns:
            Dictionary containing memory content, or None if not found
        """
        memory_path = os.path.join(self.storage_dir, f"{memory_id}.json")
        if not os.path.exists(memory_path):
            logger.warning(f"Memory not found: {memory_id}")
            return None
        
        try:
            with open(memory_path, 'r') as f:
                memory = json.load(f)
            logger.info(f"Retrieved memory: {memory_id}")
            return memory
        except Exception as e:
            logger.error(f"Error retrieving memory {memory_id}: {e}")
            return None
    
    def search_memories(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Search for memories based on tags, time range, or text.
        
        Args:
            query: Dictionary containing search parameters:
                  - tags: List of tags to match
                  - start_time: Start of time range
                  - end_time: End of time range
                  - text: Text to search for in title or summary
                  
        Returns:
            List of matching memory items (index entries only, not full content)
        """
        results = []
        
        tags = query.get("tags", [])
        start_time = query.get("start_time", 0)
        end_time = query.get("end_time", float("inf"))
        text = query.get("text", "").lower()
        
        for memory_id, memory in self.memory_index.items():
            # Check tags (if specified)
            if tags and not any(tag in memory.get("tags", []) for tag in tags):
                continue
            
            # Check time range
            timestamp = memory.get("timestamp", 0)
            if timestamp < start_time or timestamp > end_time:
                continue
            
            # Check text
            if text:
                title = memory.get("title", "").lower()
                summary = memory.get("summary", "").lower()
                if text not in title and text not in summary:
                    continue
            
            # All checks passed, add to results
            results.append(memory)
        
        # Sort by timestamp (newest first)
        results.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
        return results
    
    def update_memory(self, memory_id: str, updates: Dict[str, Any]) -> str:
        """
        Update an existing memory.
        
        Args:
            memory_id: ID of the memory to update
            updates: Dictionary containing fields to update
            
        Returns:
            Success or error message
        """
        # Check if memory exists
        existing_memory = self.retrieve_memory(memory_id)
        if not existing_memory:
            return f"Error: Memory {memory_id} not found"
        
        # Update memory
        for key, value in updates.items():
            existing_memory[key] = value
        
        # Update timestamp
        existing_memory["last_updated"] = time.time()
        
        # Update index
        self.memory_index[memory_id] = {
            "id": memory_id,
            "title": existing_memory.get("title", "Untitled Memory"),
            "tags": existing_memory.get("tags", []),
            "timestamp": existing_memory.get("timestamp", 0),
            "last_updated": existing_memory.get("last_updated", 0),
            "summary": existing_memory.get("summary", "")
        }
        
        # Save updated memory
        memory_path = os.path.join(self.storage_dir, f"{memory_id}.json")
        try:
            with open(memory_path, 'w') as f:
                json.dump(existing_memory, f, indent=2)
            logger.info(f"Updated memory: {memory_id}")
            self.save_index()
            return f"Successfully updated memory: {memory_id}"
        except Exception as e:
            logger.error(f"Error updating memory {memory_id}: {e}")
            return f"Error: {e}"
    
    def delete_memory(self, memory_id: str) -> str:
        """
        Delete a memory.
        
        Args:
            memory_id: ID of the memory to delete
            
        Returns:
            Success or error message
        """
        # Check if memory exists in index
        if memory_id not in self.memory_index:
            return f"Error: Memory {memory_id} not found"
        
        # Remove from index
        del self.memory_index[memory_id]
        
        # Remove file
        memory_path = os.path.join(self.storage_dir, f"{memory_id}.json")
        try:
            if os.path.exists(memory_path):
                os.remove(memory_path)
            logger.info(f"Deleted memory: {memory_id}")
            self.save_index()
            return f"Successfully deleted memory: {memory_id}"
        except Exception as e:
            logger.error(f"Error deleting memory {memory_id}: {e}")
            return f"Error: {e}"

# Initialize memory storage
memory_storage = MemoryStorage(storage_dir="memory_storage")

@function_tool
def store_memory(title: str, content: str, tags: str = "", summary: str = "", links: str = "") -> str:
    """
    Store a new memory with the given content and metadata.
    
    Args:
        title: Title of the memory
        content: Main content of the memory
        tags: Comma-separated list of tags (optional)
        summary: Brief summary of the memory (optional)
        links: JSON string containing related links (optional)
              Format: [{"title": "Link Title", "url": "https://example.com"}, ...]
        
    Returns:
        The memory ID if successful, or an error message
    """
    logger.info(f"Storing new memory: {title}")
    
    # Parse tags
    tag_list = [tag.strip() for tag in tags.split(",")] if tags else []
    
    # Parse links
    link_list = []
    if links:
        try:
            link_list = json.loads(links)
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON format for links: {links}")
            return "Error: Invalid JSON format for links"
    
    # Generate a unique ID
    memory_id = f"mem_{int(time.time())}_{hash(title) % 10000:04d}"
    
    # Create memory object
    memory = {
        "title": title,
        "content": content,
        "tags": tag_list,
        "summary": summary,
        "links": link_list,
        "timestamp": time.time()
    }
    
    # Store memory
    result = memory_storage.store_memory(memory_id, memory)
    return result

@function_tool
def retrieve_memory(memory_id: str) -> str:
    """
    Retrieve a memory by its ID.
    
    Args:
        memory_id: ID of the memory to retrieve
        
    Returns:
        JSON string containing the memory content, or an error message
    """
    logger.info(f"Retrieving memory: {memory_id}")
    
    memory = memory_storage.retrieve_memory(memory_id)
    if memory:
        return json.dumps(memory, indent=2)
    else:
        return f"Error: Memory {memory_id} not found"

@function_tool
def search_memories(query: str) -> str:
    """
    Search for memories based on tags, time range, or text.
    
    Args:
        query: JSON string containing search parameters:
              {
                "tags": ["tag1", "tag2"],  # optional
                "start_time": 1617235200,  # optional, unix timestamp
                "end_time": 1617321600,    # optional, unix timestamp
                "text": "search text"      # optional
              }
              
    Returns:
        JSON string containing matching memories (index entries only)
    """
    logger.info(f"Searching memories with query: {query}")
    
    try:
        search_params = json.loads(query)
    except json.JSONDecodeError:
        return "Error: Invalid JSON query"
    
    results = memory_storage.search_memories(search_params)
    return json.dumps({"count": len(results), "results": results}, indent=2)

@function_tool
def update_memory(memory_id: str, updates: str) -> str:
    """
    Update an existing memory.
    
    Args:
        memory_id: ID of the memory to update
        updates: JSON string containing fields to update:
                {
                  "title": "New title",       # optional
                  "content": "New content",   # optional
                  "tags": ["tag1", "tag2"],   # optional
                  "summary": "New summary"    # optional
                }
                
    Returns:
        Success or error message
    """
    logger.info(f"Updating memory: {memory_id}")
    
    try:
        update_data = json.loads(updates)
    except json.JSONDecodeError:
        return "Error: Invalid JSON updates"
    
    result = memory_storage.update_memory(memory_id, update_data)
    return result

@function_tool
def delete_memory(memory_id: str) -> str:
    """
    Delete a memory.
    
    Args:
        memory_id: ID of the memory to delete
        
    Returns:
        Success or error message
    """
    logger.info(f"Deleting memory: {memory_id}")
    
    result = memory_storage.delete_memory(memory_id)
    return result

@function_tool
def ingest_file_to_memory(file_handle: str, title: str = "", tags: str = "") -> str:
    """
    Read a file and store its content as a memory.
    
    Args:
        file_handle: Handle of the file to ingest
        title: Title for the memory (defaults to filename if not provided)
        tags: Comma-separated list of tags (optional)
        
    Returns:
        The memory ID if successful, or an error message
    """
    logger.info(f"Ingesting file to memory: {file_handle}")
    
    try:
        # Get the file content
        file_bytes = storage_service.download_file(file_handle)
        
        # Determine file type based on extension
        file_extension = os.path.splitext(file_handle)[1].lower()
        
        # Process based on file type
        if file_extension in ['.txt', '.md']:
            content = file_bytes.decode('utf-8', errors='replace')
        else:
            return f"Error: Unsupported file type for memory ingestion: {file_extension}"
        
        # Use filename as title if not provided
        if not title:
            title = os.path.basename(file_handle)
        
        # Generate summary (first 200 chars)
        summary = content[:200] + "..." if len(content) > 200 else content
        
        # Store as memory
        tag_list = [tag.strip() for tag in tags.split(",")] if tags else []
        tag_list.append(f"file_type:{file_extension[1:]}")
        
        # Generate a unique ID
        memory_id = f"mem_file_{int(time.time())}_{hash(title) % 10000:04d}"
        
        # Create memory object
        memory = {
            "title": title,
            "content": content,
            "tags": tag_list,
            "summary": summary,
            "source_file": file_handle,
            "timestamp": time.time()
        }
        
        # Store memory
        result = memory_storage.store_memory(memory_id, memory)
        return result
        
    except FileNotFoundError:
        logger.error(f"File not found: {file_handle}")
        return f"Error: File not found: {file_handle}"
    except Exception as e:
        logger.exception(f"Error ingesting file {file_handle}: {e}")
        return f"Error ingesting file: {e}"

@function_tool
def store_link(title: str, url: str, description: str = "", tags: str = "") -> str:
    """
    Store a link as a memory item.
    
    Args:
        title: Title of the link
        url: URL of the link
        description: Description of the link (optional)
        tags: Comma-separated list of tags (optional)
        
    Returns:
        The memory ID if successful, or an error message
    """
    logger.info(f"Storing link: {title} - {url}")
    
    # Parse tags
    tag_list = [tag.strip() for tag in tags.split(",")] if tags else []
    tag_list.append("link")  # Add 'link' tag to all link memories
    
    # Generate a unique ID
    memory_id = f"link_{int(time.time())}_{hash(url) % 10000:04d}"
    
    # Create memory object
    memory = {
        "title": title,
        "content": description,
        "url": url,
        "tags": tag_list,
        "type": "link",
        "timestamp": time.time()
    }
    
    # Store memory
    result = memory_storage.store_memory(memory_id, memory)
    return result

@function_tool
def get_links_by_tag(tag: str) -> str:
    """
    Retrieve links filtered by tag.
    
    Args:
        tag: Tag to filter by
        
    Returns:
        JSON string containing matching links
    """
    logger.info(f"Retrieving links with tag: {tag}")
    
    search_params = {
        "tags": [tag, "link"],  # Must have both the specified tag and the 'link' tag
    }
    
    results = memory_storage.search_memories(search_params)
    return json.dumps({"count": len(results), "links": results}, indent=2)
