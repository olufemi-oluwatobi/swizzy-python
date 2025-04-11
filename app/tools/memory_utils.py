"""
Utility functions for memory management across agents.
"""
import logging
from typing import Dict, List, Any, Optional
from app.tools.memory_tools import store_memory, store_link, get_links_by_tag

logger = logging.getLogger(__name__)

def log_agent_action(
    agent_name: str,
    action_type: str,
    action_details: Dict[str, Any],
    outcome: str,
    tags: List[str] = None
) -> str:
    """
    Logs an agent action or decision to the memory system.
    
    Args:
        agent_name: Name of the agent performing the action
        action_type: Type of action (e.g., 'search', 'extraction', 'conversion')
        action_details: Dictionary containing details about the action
        outcome: Description of the action outcome
        tags: List of tags to categorize the memory
        
    Returns:
        The memory ID of the stored memory
    """
    logger.info(f"Logging agent action: {agent_name} - {action_type}")
    
    # Create default tags if none provided
    if tags is None:
        tags = []
    
    # Always include agent name and action type in tags
    if agent_name.lower().replace(" ", "_") not in tags:
        tags.append(agent_name.lower().replace(" ", "_"))
    if action_type.lower().replace(" ", "_") not in tags:
        tags.append(action_type.lower().replace(" ", "_"))
    
    # Add 'agent_action' tag for easy filtering
    if "agent_action" not in tags:
        tags.append("agent_action")
    
    # Create memory content
    memory_content = {
        "agent": agent_name,
        "action_type": action_type,
        "details": action_details,
        "outcome": outcome,
        "timestamp": "auto"  # The memory system will add the current timestamp
    }
    
    # Create memory title
    memory_title = f"{agent_name}: {action_type} - {action_details.get('summary', 'No summary provided')}"
    
    # Store the memory
    memory_id = store_memory(memory_title, memory_content, tags)
    
    return memory_id

def log_research_finding(
    topic: str,
    source_url: str,
    key_points: List[str],
    tags: List[str] = None
) -> Dict[str, str]:
    """
    Logs a research finding with both a memory entry and a link.
    
    Args:
        topic: Research topic
        source_url: URL of the source
        key_points: List of key points from the source
        tags: List of tags to categorize the memory and link
        
    Returns:
        Dictionary containing the memory ID and link ID
    """
    logger.info(f"Logging research finding for topic: {topic}")
    
    # Create default tags if none provided
    if tags is None:
        tags = []
    
    # Always include research tags
    if "research" not in tags:
        tags.append("research")
    if topic.lower().replace(" ", "_") not in tags:
        tags.append(topic.lower().replace(" ", "_"))
    
    # Create memory content
    memory_content = {
        "topic": topic,
        "source_url": source_url,
        "key_points": key_points,
        "timestamp": "auto"  # The memory system will add the current timestamp
    }
    
    # Create memory title
    memory_title = f"Research: {topic} - {key_points[0] if key_points else 'No key points provided'}"
    
    # Store the memory
    memory_id = store_memory(memory_title, memory_content, tags)
    
    # Store the link
    link_id = store_link(source_url, f"Research source for {topic}", tags)
    
    return {
        "memory_id": memory_id,
        "link_id": link_id
    }

def log_data_extraction(
    file_handle: str,
    extraction_type: str,
    extraction_details: Dict[str, Any],
    output_file_handle: Optional[str] = None,
    tags: List[str] = None
) -> str:
    """
    Logs a data extraction operation to the memory system.
    
    Args:
        file_handle: Handle of the file data was extracted from
        extraction_type: Type of extraction performed (e.g., 'invoice', 'table')
        extraction_details: Dictionary containing details about the extraction
        output_file_handle: Handle of the output file (if applicable)
        tags: List of tags to categorize the memory
        
    Returns:
        The memory ID of the stored memory
    """
    logger.info(f"Logging data extraction: {extraction_type} from {file_handle}")
    
    # Create default tags if none provided
    if tags is None:
        tags = []
    
    # Always include data extraction tags
    if "data_extraction" not in tags:
        tags.append("data_extraction")
    if extraction_type.lower().replace(" ", "_") not in tags:
        tags.append(extraction_type.lower().replace(" ", "_"))
    
    # Create memory content
    memory_content = {
        "file_handle": file_handle,
        "extraction_type": extraction_type,
        "details": extraction_details,
        "output_file_handle": output_file_handle,
        "timestamp": "auto"  # The memory system will add the current timestamp
    }
    
    # Create memory title
    memory_title = f"Data Extraction: {extraction_type} from {file_handle}"
    
    # Store the memory
    memory_id = store_memory(memory_title, memory_content, tags)
    
    return memory_id

def log_document_operation(
    operation_type: str,
    file_handle: str,
    details: Dict[str, Any],
    output_file_handle: Optional[str] = None,
    tags: List[str] = None
) -> str:
    """
    Logs a document operation to the memory system.
    
    Args:
        operation_type: Type of operation (e.g., 'create', 'edit', 'convert')
        file_handle: Handle of the file operated on
        details: Dictionary containing details about the operation
        output_file_handle: Handle of the output file (if applicable)
        tags: List of tags to categorize the memory
        
    Returns:
        The memory ID of the stored memory
    """
    logger.info(f"Logging document operation: {operation_type} on {file_handle}")
    
    # Create default tags if none provided
    if tags is None:
        tags = []
    
    # Always include document operation tags
    if "document_operation" not in tags:
        tags.append("document_operation")
    if operation_type.lower().replace(" ", "_") not in tags:
        tags.append(operation_type.lower().replace(" ", "_"))
    
    # Create memory content
    memory_content = {
        "operation_type": operation_type,
        "file_handle": file_handle,
        "details": details,
        "output_file_handle": output_file_handle,
        "timestamp": "auto"  # The memory system will add the current timestamp
    }
    
    # Create memory title
    memory_title = f"Document Operation: {operation_type} on {file_handle}"
    
    # Store the memory
    memory_id = store_memory(memory_title, memory_content, tags)
    
    return memory_id
