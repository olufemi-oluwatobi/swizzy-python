"""
Tools for research planning and execution.
"""
import os
import logging
import json
import time
from typing import Dict, List, Any, Optional
from app.tools.web_tools import search_web, search_with_budget, read_url, extract_url_to_markdown
from app.tools.content_tools import create_markdown
from app.tools.memory_tools import store_memory, store_link, get_links_by_tag
from app.tools.memory_utils import log_agent_action, log_research_finding
from agents import function_tool
from app.services.gemini_service import GeminiService

logger = logging.getLogger(__name__)

@function_tool
def plan_research(research_topic: str, max_budget: float = 1.0) -> str:
    """
    Creates a structured research plan for a given topic using Google Gemini.
    
    Args:
        research_topic: The topic to research
        max_budget: Maximum budget for the research in dollars
        
    Returns:
        JSON string containing the research plan
    """
    logger.info(f"Planning research for topic: {research_topic}")
    
    try:
        # Initialize Gemini service
        gemini_service = GeminiService()
        
        # Create a prompt for generating a research plan
        prompt = f"""
        Create a comprehensive research plan for the topic: "{research_topic}"
        
        The plan should be structured as a JSON object with the following format:
        {{
            "topic": "{research_topic}",
            "max_budget": {max_budget},
            "created_at": [current timestamp],
            "subtopics": [
                {{
                    "name": "Name of subtopic 1",
                    "search_queries": ["query 1", "query 2", "query 3"],
                    "priority": "high/medium/low"
                }},
                // More subtopics...
            ],
            "budget_allocation": {{
                "high_priority": [50% of max_budget],
                "medium_priority": [30% of max_budget],
                "low_priority": [20% of max_budget]
            }}
        }}
        
        Include 4-6 subtopics that comprehensively cover the research topic.
        For each subtopic, include 2-4 search queries that would yield relevant information.
        Assign priorities (high, medium, low) based on the importance of each subtopic.
        
        The plan should be detailed, well-structured, and ready to be executed by a research agent.
        """
        
        # Use Gemini to generate the research plan
        result = gemini_service.analyze_image(b"", prompt)  # Using empty bytes as we're just using text
        
        if result.get("success"):
            # Try to parse JSON from the response
            text = result["text"]
            json_start = text.find('{')
            json_end = text.rfind('}')
            
            if json_start >= 0 and json_end > json_start:
                json_str = text[json_start:json_end+1]
                
                # Parse the JSON to validate it
                plan = json.loads(json_str)
                
                # Ensure all required fields are present
                if "topic" not in plan:
                    plan["topic"] = research_topic
                if "max_budget" not in plan:
                    plan["max_budget"] = max_budget
                if "created_at" not in plan:
                    plan["created_at"] = time.time()
                
                # Ensure budget allocation is correct
                if "budget_allocation" not in plan:
                    plan["budget_allocation"] = {
                        "high_priority": max_budget * 0.5,
                        "medium_priority": max_budget * 0.3,
                        "low_priority": max_budget * 0.2
                    }
                
                # Log the plan creation
                log_agent_action(
                    agent_name="Research Agent",
                    action_type="plan_creation",
                    action_details={
                        "topic": research_topic,
                        "max_budget": max_budget,
                        "subtopics_count": len(plan.get("subtopics", [])),
                        "plan_summary": f"Research plan for {research_topic} with {len(plan.get('subtopics', []))} subtopics"
                    },
                    outcome="Created research plan using Gemini",
                    tags=["research", "planning", research_topic.lower().replace(" ", "_")]
                )
                
                return json.dumps(plan, indent=2)
            else:
                # If no valid JSON found, create a default plan
                return _create_default_research_plan(research_topic, max_budget)
        else:
            # If Gemini fails, create a default plan
            error_message = result.get("error", "Unknown error")
            logger.error(f"Error generating research plan with Gemini: {error_message}")
            return _create_default_research_plan(research_topic, max_budget)
        
    except Exception as e:
        logger.exception(f"Error planning research: {e}")
        
        # Log the error
        log_agent_action(
            agent_name="Research Agent",
            action_type="plan_creation_error",
            action_details={
                "topic": research_topic,
                "max_budget": max_budget,
                "error": str(e)
            },
            outcome=f"Error creating research plan: {e}",
            tags=["research", "planning", "error"]
        )
        
        # Fall back to default plan
        return _create_default_research_plan(research_topic, max_budget)

def _create_default_research_plan(research_topic: str, max_budget: float) -> str:
    """
    Creates a default research plan when Gemini fails.
    
    Args:
        research_topic: The topic to research
        max_budget: Maximum budget for the research in dollars
        
    Returns:
        JSON string containing the default research plan
    """
    # Create a plan with subtopics and search queries
    plan = {
        "topic": research_topic,
        "max_budget": max_budget,
        "created_at": time.time(),
        "subtopics": [
            {
                "name": f"Overview of {research_topic}",
                "search_queries": [
                    f"{research_topic} overview",
                    f"{research_topic} introduction",
                    f"what is {research_topic}"
                ],
                "priority": "high"
            },
            {
                "name": f"Key aspects of {research_topic}",
                "search_queries": [
                    f"{research_topic} key components",
                    f"{research_topic} important elements",
                    f"{research_topic} main features"
                ],
                "priority": "high"
            },
            {
                "name": f"Recent developments in {research_topic}",
                "search_queries": [
                    f"{research_topic} latest developments",
                    f"{research_topic} recent advances",
                    f"{research_topic} new research"
                ],
                "priority": "medium"
            },
            {
                "name": f"Challenges and limitations of {research_topic}",
                "search_queries": [
                    f"{research_topic} challenges",
                    f"{research_topic} limitations",
                    f"{research_topic} problems"
                ],
                "priority": "medium"
            },
            {
                "name": f"Future of {research_topic}",
                "search_queries": [
                    f"{research_topic} future",
                    f"{research_topic} trends",
                    f"{research_topic} predictions"
                ],
                "priority": "low"
            }
        ],
        "budget_allocation": {
            "high_priority": max_budget * 0.5,
            "medium_priority": max_budget * 0.3,
            "low_priority": max_budget * 0.2
        }
    }
    
    # Log the default plan creation
    log_agent_action(
        agent_name="Research Agent",
        action_type="default_plan_creation",
        action_details={
            "topic": research_topic,
            "max_budget": max_budget,
            "subtopics_count": len(plan["subtopics"]),
            "plan_summary": f"Default research plan for {research_topic}"
        },
        outcome="Created default research plan",
        tags=["research", "planning", "default_plan", research_topic.lower().replace(" ", "_")]
    )
    
    return json.dumps(plan, indent=2)

@function_tool
def execute_research_plan(plan_json: str, output_filename: str = "research_results.md") -> str:
    """
    Executes a research plan and compiles the results into a Markdown document.
    
    Args:
        plan_json: JSON string containing the research plan
        output_filename: Name for the output Markdown file
        
    Returns:
        The file handle of the created Markdown file
    """
    logger.info(f"Executing research plan")
    
    try:
        # Parse the research plan
        plan = json.loads(plan_json)
        
        # Initialize variables for tracking
        topic = plan["topic"]
        max_budget = plan["max_budget"]
        budget_used = 0.0
        research_results = []
        
        # Log the start of research execution
        log_agent_action(
            agent_name="Research Agent",
            action_type="research_execution_start",
            action_details={
                "topic": topic,
                "max_budget": max_budget,
                "subtopics_count": len(plan["subtopics"]),
                "plan": plan
            },
            outcome="Started executing research plan",
            tags=["research", "plan_execution", topic.lower().replace(" ", "_")]
        )
        
        # Create the document structure
        document_content = f"# Research: {topic}\n\n"
        document_content += f"*Generated on {time.strftime('%Y-%m-%d %H:%M:%S')}*\n\n"
        document_content += f"## Executive Summary\n\n"
        document_content += f"This document contains research findings on {topic}.\n\n"
        
        # Process each subtopic
        for subtopic in plan["subtopics"]:
            subtopic_name = subtopic["name"]
            priority = subtopic["priority"]
            search_queries = subtopic["search_queries"]
            
            # Determine budget for this subtopic
            if priority == "high":
                subtopic_budget = plan["budget_allocation"]["high_priority"] / len([s for s in plan["subtopics"] if s["priority"] == "high"])
            elif priority == "medium":
                subtopic_budget = plan["budget_allocation"]["medium_priority"] / len([s for s in plan["subtopics"] if s["priority"] == "medium"])
            else:
                subtopic_budget = plan["budget_allocation"]["low_priority"] / len([s for s in plan["subtopics"] if s["priority"] == "low"])
            
            # Log subtopic research start
            log_agent_action(
                agent_name="Research Agent",
                action_type="subtopic_research_start",
                action_details={
                    "topic": topic,
                    "subtopic": subtopic_name,
                    "priority": priority,
                    "budget": subtopic_budget,
                    "queries": search_queries
                },
                outcome=f"Started researching subtopic: {subtopic_name}",
                tags=["research", "subtopic", topic.lower().replace(" ", "_"), subtopic_name.lower().replace(" ", "_")]
            )
            
            # Add subtopic to document
            document_content += f"## {subtopic_name}\n\n"
            
            # Execute searches for this subtopic
            subtopic_results = []
            for query in search_queries:
                # Check if we have enough budget
                if budget_used + 0.005 > max_budget:  # 0.005 is cost per search
                    document_content += f"*Note: Budget limit reached. Some searches were skipped.*\n\n"
                    break
                
                # Perform search
                search_result = search_with_budget(query, max_budget - budget_used)
                
                # Extract budget used
                if "Total cost:" in search_result:
                    cost_line = [line for line in search_result.split("\n") if "Total cost:" in line][0]
                    cost = float(cost_line.split("$")[1].strip())
                    budget_used = cost
                
                # Extract top result URL
                result_lines = search_result.split("\n")
                url = None
                for line in result_lines:
                    if line.startswith("1. [") and "](" in line:
                        url = line.split("](")[1].split(")")[0]
                        break
                
                if url:
                    # Extract content from URL
                    url_content = extract_url_to_markdown(url)
                    
                    # Extract key points (first few paragraphs)
                    content_lines = url_content.split("\n\n")
                    key_points = content_lines[:3] if len(content_lines) >= 3 else content_lines
                    
                    # Log the research finding
                    finding_ids = log_research_finding(
                        topic=f"{topic} - {subtopic_name}",
                        source_url=url,
                        key_points=[p.strip() for p in key_points if p.strip()],
                        tags=["research", topic.lower().replace(" ", "_"), subtopic_name.lower().replace(" ", "_"), "finding"]
                    )
                    
                    # Store the link with appropriate tags
                    link_id = finding_ids["link_id"]
                    
                    # Add to results
                    subtopic_results.append({
                        "query": query,
                        "url": url,
                        "content": url_content,
                        "link_id": link_id,
                        "memory_id": finding_ids["memory_id"]
                    })
                    
                    # Add summary to document
                    document_content += f"### Research on: {query}\n\n"
                    document_content += f"Source: [{url}]({url})\n\n"
                    
                    # Extract a summary (first few paragraphs)
                    summary = "\n\n".join(content_lines[:3]) + "\n\n"
                    document_content += summary
                    
                    # Add citation
                    document_content += f"*[Citation: {url}]*\n\n"
            
            # Add subtopic results to overall results
            research_results.append({
                "subtopic": subtopic_name,
                "results": subtopic_results
            })
            
            # Log subtopic research completion
            log_agent_action(
                agent_name="Research Agent",
                action_type="subtopic_research_complete",
                action_details={
                    "topic": topic,
                    "subtopic": subtopic_name,
                    "results_count": len(subtopic_results),
                    "budget_used": budget_used
                },
                outcome=f"Completed research on subtopic: {subtopic_name} with {len(subtopic_results)} findings",
                tags=["research", "subtopic_complete", topic.lower().replace(" ", "_"), subtopic_name.lower().replace(" ", "_")]
            )
        
        # Add budget information
        document_content += f"## Research Metadata\n\n"
        document_content += f"- **Topic:** {topic}\n"
        document_content += f"- **Budget:** ${max_budget:.2f}\n"
        document_content += f"- **Budget Used:** ${budget_used:.2f}\n"
        document_content += f"- **Completion Date:** {time.strftime('%Y-%m-%d')}\n\n"
        
        # Create the markdown file
        file_handle = create_markdown(output_filename, document_content)
        
        # Store the research in memory
        memory_id = store_memory(
            f"Research on {topic}",
            {
                "topic": topic,
                "budget": max_budget,
                "budget_used": budget_used,
                "completion_date": time.strftime('%Y-%m-%d'),
                "file_handle": file_handle
            },
            ["research", topic.lower().replace(" ", "_")]
        )
        
        # Log research completion
        log_agent_action(
            agent_name="Research Agent",
            action_type="research_complete",
            action_details={
                "topic": topic,
                "budget": max_budget,
                "budget_used": budget_used,
                "subtopics_count": len(plan["subtopics"]),
                "findings_count": sum(len(subtopic["results"]) for subtopic in research_results),
                "output_file": file_handle
            },
            outcome=f"Completed research on {topic} and created document: {file_handle}",
            tags=["research", "research_complete", topic.lower().replace(" ", "_")]
        )
        
        return file_handle
        
    except Exception as e:
        logger.exception(f"Error executing research plan: {e}")
        
        # Log the error
        log_agent_action(
            agent_name="Research Agent",
            action_type="research_error",
            action_details={
                "error": str(e)
            },
            outcome=f"Error executing research plan: {e}",
            tags=["research", "error"]
        )
        
        return f"Error executing research plan: {e}"

@function_tool
def research_topic(topic: str, max_budget: float = 1.0, output_filename: str = "") -> str:
    """
    Performs comprehensive research on a topic and creates a Markdown document with findings.
    
    Args:
        topic: The topic to research
        max_budget: Maximum budget for the research in dollars
        output_filename: Optional name for the output file
        
    Returns:
        The file handle of the created Markdown file
    """
    logger.info(f"Researching topic: {topic} with budget: ${max_budget}")
    
    try:
        # Generate default output filename if not provided
        if not output_filename:
            # Create a filename from the topic
            safe_topic = topic.lower().replace(" ", "_").replace("/", "_").replace("\\", "_")
            output_filename = f"research_{safe_topic}_{time.strftime('%Y%m%d')}.md"
        
        # Create a research plan
        plan_json = plan_research(topic, max_budget)
        
        # Execute the research plan
        file_handle = execute_research_plan(plan_json, output_filename)
        
        return file_handle
        
    except Exception as e:
        logger.exception(f"Error researching topic: {e}")
        return f"Error researching topic: {e}"
