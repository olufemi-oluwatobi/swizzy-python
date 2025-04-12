from __future__ import annotations

import json
import os
import logging
from typing import List, Optional
from pydantic import BaseModel, Field
from openai import AsyncOpenAI
# Import TaskContext and context tools from server
from app.context import TaskContext, get_task_id, log_action
from agents import Agent
from agents import WebSearchTool, function_tool, OpenAIChatCompletionsModel, handoff, GuardrailFunctionOutput, RunContextWrapper, output_guardrail
from dotenv import load_dotenv

# Import existing tools
from app.swizzy_tools import (
    create_document,
    extract_text_from_image,
    ponder_document_request,
    read_file_content,
    extract_spreadsheet_from_document
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
    model="gemini-2.0-flash", # Updated to 1.5-flash as per previous context, adjust if needed
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

# Agent for Documents (Create) - Updated with TaskContext and tools
document_agent = Agent[TaskContext]( # <--- Added TaskContext type hint
    name="Document Specialist",
    model=gemini_model,
    instructions="".join([
        "You are a specialist in dealing with document files, with **Markdown documents (.md) as your primary format**. You also possess strong capabilities for handling other common formats like **Microsoft Word (.docx), Portable Document Format (.pdf), and plain text (.txt)**, as well as **extracting text from images**. ",
        "Your primary responsibility is to produce high-quality Markdown documents that meet client requirements, and to manage conversions, interactions, and content extraction from various document formats effectively. ",
        "You MUST use the `get_task_id` tool to get the current task ID and prepend it to any filename you create (e.g., `[task_id]_report.md`). ",
        "You MUST log significant actions using the `log_action` tool. ",
        "**MARKDOWN IS YOUR CENTRAL LANGUAGE** - you should always prefer working with Markdown files for maximum flexibility and editability. You are equipped with tools to **read, edit, add content to, and modify document files**, and **extract text from images**, based on user requests.",
        "**Workflow for Different Formats:**",
        "   - **Reading:**",
        "       - You can directly access the content of various file types using the appropriate tools.",
        "       - For `.md` and `.txt` files, use the `read_markdown` tool to read content while preserving Markdown structure.",
        "       - For `.docx` and `.pdf` files, use the appropriate tool/capability to **read their text content directly**. Conversion is **NOT** required just for reading.", 
        "       - For image files (e.g., .png, .jpg), use the `extract_text_from_image` tool.", 
        "   - **Editing:**",
        "       - Edit `.md` files directly using `edit_markdown_section`.",
        "       - To **edit** `.docx` or `.pdf` files, you **MUST first convert them to Markdown** using `convert_to_markdown`. Perform edits on the Markdown version using `edit_markdown_section`. Only convert back to the original format (`.docx`, `.pdf`) using `convert_file_format` if specifically requested by the user. (Reading them first does *not* require conversion).", 
        "   - **Creating:**",
        "       - When creating new documents for users, **always prefer creating them in Markdown format** (`.md`) using `create_markdown` for maximum future editability. Ensure the filename follows the `[task_id]_your_filename.md` pattern.",

        "**CRITICAL: ALWAYS PONDER FIRST!**",
        "Before taking ANY action, you MUST:",
        "1. Use the ponder_task tool to analyze the request"
        "2. Store the pondering results using store_memory",
        "3. Log this pondering action using log_action.",
        "4. Follow the recommended approach from pondering",
        "**CRITICAL RULES**: ",
        "1. NEVER skip the pondering step - ALWAYS call ponder_document_request first ",
        "2. NEVER skip logging actions - use log_action for pondering and tool use.",
        "3. **FILENAME FORMAT**: ALWAYS use `get_task_id` and format filenames as `[task_id]_your_filename.ext` when creating files.",
        "4. NEVER claim to have read, created, or modified a file without ACTUALLY CALLING THE CORRESPONDING TOOL ",
        "5. NEVER make up fake data or pretend to analyze a file you haven't read with the tool ",
        "6. NEVER tell clients to wait - either complete the task with your tools or report an error ",
        "For each request type: ",
        "- GET TASK ID: Use get_task_id before creating any file.",
        "- LOG ACTION: Use log_action after pondering and after using a main tool.",
        "- READ (Markdown/Text): Use `read_markdown` with the file handle (specifically for `.md` and `.txt`).", 
        "- READ (Other Formats): Use the appropriate underlying capability/tool to access text content directly from `.docx`, `.pdf`, etc. Conversion is NOT required for reading only.", 
        "- CREATE: Use `create_markdown` with content (filename MUST be `[task_id]_your_filename.md`)",
        "- EDIT: Use `edit_markdown_section` to make targeted changes (on `.md` files; requires prior conversion for `.docx`/`.pdf`).", 
        "- CONVERT: Use `convert_to_markdown` or `convert_file_format` (output filename MUST be `[task_id]_your_filename.ext`)",
        "- ANALYZE: Use `analyze_content_structure` to understand document organization (primarily on `.md` files, or after conversion)",
        "- EXTRACT: Use `extract_text_from_image` with the file handle for image files.", 
        "**IMPORTANT: LOGGING ACTIONS AND DECISIONS**",
        "- ALWAYS log your significant actions and decisions using the log_action tool",
        "- Use store_memory for detailed reasoning or complex state preservation.",
        "- Include links to relevant resources using the store_link tool"
    ]),
    tools=[
        # Context Tools FIRST
        get_task_id,
        log_action,
        # Core/Pondering Tools
        ponder_task,
        ponder_document_request,
        # Memory tools
        store_memory,
        retrieve_memory,
        update_memory,
        delete_memory,
        search_memories,
        store_link,
        get_links_by_tag,
         # Document/Content tools
        read_file_content, # Keep general read
        create_document, # Keep general create? Maybe remove if create_markdown is primary
        extract_text_from_image,
        read_markdown,
        create_markdown, # Primary creation tool
        edit_markdown_section,
        convert_file_format, # Handles output conversion
        analyze_content_structure,
        # Conversion tools (Input to Markdown)
        convert_pdf_to_markdown,
        convert_to_markdown,
    ],
)
