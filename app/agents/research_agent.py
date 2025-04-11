from __future__ import annotations

import json
import os
import logging
from typing import List, Optional
from pydantic import BaseModel, Field
from openai import AsyncOpenAI
# Import TaskContext and context tools from server
from server import TaskContext, get_task_id, log_action
from agents import Agent
from agents import WebSearchTool, function_tool, OpenAIChatCompletionsModel, handoff, GuardrailFunctionOutput, RunContextWrapper, output_guardrail
from dotenv import load_dotenv

# Import existing tools
from app.swizzy_tools import (
    create_document,
    extract_text_from_image,
    ponder_document_request,
    read_file_content,
)
from app.tools import (
    analyze_spreadsheet,
    create_spreadsheet,
    modify_spreadsheet,
    ponder_spreadsheet_request,
)
from app.tools.content_tools import (
    convert_pdf_to_markdown,
    convert_to_markdown,
    read_markdown,
    edit_markdown_section,
    analyze_content_structure,
    convert_file_format,
    create_markdown
)
from app.tools.web_tools import (
    read_url,
    extract_url_to_markdown,
    search_web,
    search_with_budget,
    reset_search_budget,
    get_search_cost_summary
)
from app.tools.research_tools import (
    plan_research,
    execute_research_plan,
    research_topic
)
from app.tools.data_extraction_tools import (
    extract_structured_data,
    convert_json_to_excel,
    extract_invoice_to_excel,
    extract_table_from_document
)
from app.tools.memory_tools import (
    store_memory,
    retrieve_memory,
    update_memory,
    delete_memory,
    search_memories,
    store_link,
    get_links_by_tag
)
from app.tools.core_tools import ponder_task
from app.config import STYLE_INSTRUCTIONS

logger = logging.getLogger(__name__)

# Load environment variables if not already loaded
load_dotenv()

# Verify environment variables and setup OpenAI client for Gemini
api_key = os.getenv("GOOGLE_API_KEY") # Assuming Gemini uses GOOGLE_API_KEY based on prior context
base_url = os.getenv("OPENAI_BASE_URL") # Assuming a proxy/custom base URL

if not api_key or not base_url:
    raise ValueError("Missing required environment variables: GOOGLE_API_KEY and OPENAI_BASE_URL must be set")

# Create custom OpenAI client
client = AsyncOpenAI(
    api_key=api_key,
    base_url=base_url
)

# Create the model configuration for Gemini
gemini_model = OpenAIChatCompletionsModel(
    model="gemini-1.5-flash", # Updated to 1.5-flash as per previous context, adjust if needed
    openai_client=client,
)

# --- Define Output Model ---
class SwizzyOutput(BaseModel):
    reasoning: str = Field(description="Brief reasoning for the chosen action (tool use or handoff).")
    action_taken: str = Field(description="Description of the action performed (e.g., 'Used read_file_content', 'Handed off to spreadsheet_agent', 'Executed analysis script').")
    outcome: str = Field(description="Summary of the outcome (e.g., 'Success', 'Completed analysis', 'Error occurred', 'Handoff initiated').")
    response_to_user: str = Field(description="The final message to convey to the user.")
    generated_handles: Optional[List[str]] = Field(default=None, description="List of new file handles generated by a specialist agent, if any.")
    error_details: Optional[str] = Field(default=None, description="Details of any error encountered during tool use or handoff, if applicable.")
    task_context_id: Optional[str] = Field(default=None, description="Unique ID for the current task context, if available.")

# Research Agent Configuration - Updated with TaskContext and tools
research_agent = Agent[TaskContext]( # <--- Added TaskContext type hint
    name="Research Agent",
    model=gemini_model,
    instructions="".join([
        "You are a Research Agent, specialized in performing comprehensive research on any topic. ",
        "Your goal is to create well-structured, informative reports with proper citations. ",
        "You MUST use the `get_task_id` tool to get the current task ID and prepend it to any filename you create (e.g., `[task_id]_research_report.md`). ",
        "You MUST log significant actions using the `log_action` tool. ",
        # ...(rest of instructions remain the same)...
        "**WORKFLOW**: ",
        "1. When given a research topic, first create a research plan (log action) ",
        "2. Execute the plan by searching for information on each subtopic (log actions/findings) ",
        "3. Extract relevant content from the top search results (log actions/sources) ",
        "4. Compile findings into a well-structured Markdown document (use get_task_id for filename, log action) ",
        "5. Include proper citations for all information sources ",
        "6. Return the file handle of the created document (`[task_id]_filename.md`) ",
        # ...(rest of instructions remain the same)...
        "For each request type: ",
        "- GET TASK ID: Use get_task_id before creating any file.",
        "- LOG ACTION: Use log_action after pondering, planning, searching, and compiling.",
        "- PLAN: Use plan_research to create a structured research plan ",
        "- EXECUTE: Use execute_research_plan to execute a research plan ",
        "- SEARCH: Use search_web or search_with_budget to search for information ",
        "- READ: Use read_url or extract_url_to_markdown to extract content from URLs ",
        "- ALL-IN-ONE: Use research_topic (ensure it uses get_task_id for output filename internally, log action) ",
        "- COMPILE: Use create_markdown (filename MUST be `[task_id]_your_filename.md`) ",
         # ...(rest of instructions remain the same)...
        "**IMPORTANT: LOGGING ACTIONS AND DECISIONS**",
        "- ALWAYS log your significant actions and decisions using the log_action tool",
        "- Use store_memory for detailed reasoning or complex state preservation.",
        "- Include links to valuable sources using the store_link tool"
    ]),
    tools=[
        # Context Tools FIRST
        get_task_id,
        log_action,
        # Core/Pondering Tools
        ponder_task,
        # Memory tools
        store_memory,
        retrieve_memory,
        update_memory,
        delete_memory,
        search_memories,
        store_link,
        get_links_by_tag,
        # Research tools
        plan_research,
        execute_research_plan,
        research_topic,
        # Web tools
        search_web,
        search_with_budget,
        reset_search_budget,
        get_search_cost_summary,
        read_url,
        extract_url_to_markdown,
        # Content tools
        read_markdown,
        create_markdown, # For compiling report
        read_file_content # General read if needed
    ],
)
