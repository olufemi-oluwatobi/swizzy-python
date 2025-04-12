from __future__ import annotations

import json
import os
import logging
from typing import List, Optional
from pydantic import BaseModel, Field
from openai import AsyncOpenAI
# Import TaskContext and context tools from server
from app.context import TaskContext, get_task_id, log_action, inspect_context, log_file_action
from agents import Agent
from agents import WebSearchTool, function_tool, OpenAIChatCompletionsModel, handoff, GuardrailFunctionOutput, RunContextWrapper, output_guardrail
from dotenv import load_dotenv

# Import existing tools
from app.swizzy_tools import (
    create_document,
    extract_text_from_image,
    ponder_document_request,
    read_file_content,
    extract_spreadsheet_from_document,  # Add new tool
)
from app.tools import (
    analyze_spreadsheet,
    create_spreadsheet,
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
from app.agents.model_config import gemini_model  # Import shared model config
from app.agents.spreadsheet_analysis_agent import spreadsheet_analysis_agent
from app.tools.run_spreadsheet_operation import run_spreadsheet_operation

logger = logging.getLogger(__name__)

# --- Define Output Model ---
class SwizzyOutput(BaseModel):
    reasoning: str = Field(description="Brief reasoning for the chosen action (tool use or handoff).")
    action_taken: str = Field(description="Description of the action performed (e.g., 'Used read_file_content', 'Handed off to spreadsheet_agent', 'Executed analysis script').")
    outcome: str = Field(description="Summary of the outcome (e.g., 'Success', 'Completed analysis', 'Error occurred', 'Handoff initiated').")
    response_to_user: str = Field(description="The final message to convey to the user.")
    generated_handles: Optional[List[str]] = Field(default=None, description="List of new file handles generated by a specialist agent, if any.")
    error_details: Optional[str] = Field(default=None, description="Details of any error encountered during tool use or handoff, if applicable.")
    task_context_id: Optional[str] = Field(default=None, description="Unique ID for the current task context, if available.")

# Agent for Spreadsheets (Create/Modify) - Updated with TaskContext and tools
spreadsheet_agent = Agent[TaskContext](  # <--- Added TaskContext type hint
    name="Spreadsheet Specialist",
    instructions=''.join([
        "You are a specialist in dealing with spreadsheets (.xlsx, .csv). Your primary responsibility is to produce high-quality spreadsheet files that meet client requirements. ",
        "You MUST use the `get_task_id` tool to get the current task ID and prepend it to any filename you create (e.g., `[task_id]_budget.xlsx`). ",
        "You MUST log significant actions using the `log_action` tool. ",
        "**CRITICAL: ALWAYS PONDER FIRST!**",
        "Before taking ANY action, you MUST:",
        "1. Use the ponder_task tool to analyze the request",
        "2. Store the pondering results using store_memory",
        "3. Log this pondering action using log_action.",
        "4. Follow the recommended approach from pondering",
        "You MUST use the `ponder_spreadsheet_request` tool to think through the request and determine the best approach. ",
        "You  Must log all files created or modified using the `log_file_action` tool. ",
        "**CRITICAL: ALWAYS THINK BEFORE YOU ACT!** You must use the ponder_spreadsheet_request tool FIRST before taking any action. ",
        "Your workflow must ALWAYS follow this sequence: ",
        "1. PONDER: Use ponder_spreadsheet_request to think through the request and determine the best approach ",
        "2. LOG PONDERING: Use log_action to record the pondering outcome.",
        "3. ACT: Based on the pondering results, use the appropriate spreadsheet tools (remembering to use get_task_id for filenames) ",
        "4. LOG ACTION: Use log_action to record the specific spreadsheet action taken.",
        "5. RESPOND: Provide a comprehensive response to the client ",
        "You have these tools at your disposal: ",
        "- get_task_id: MUST be called before creating files to get the task ID for the filename.",
        "- log_action: MUST be called to log pondering and spreadsheet actions.",
        "- ponder_spreadsheet_request: MUST be called FIRST to think through the request ",
        "- read_file_content: Use this to read existing spreadsheet files excel files, csv files etc.",
        "- create_spreadsheet: Use this to create new spreadsheets (filename MUST be `[task_id]_your_filename.xlsx`).",
        "- analyze_spreadsheet: Use this to perform complex analysis operations on spreadsheets ",
        "- extract_spreadsheet_from_document: Use this to extract spreadsheet data from documents (e.g., PDF), We can read documets and caputree thee table in them ideeal for invoices, bank statments and any job for extracting tables from documents",
        "- run_spreadsheet_operation: Executes a custom operation on a spreadsheet based on the given instruction. Use this tool to modify or take actions on spreadsheet. Ensure you provide very clear and detailed instruction.",
        "- inspect_context: Use this to inspect the current context and understand the task better.  If a file is not found there is a likelihood that the accurate file handle was not provided to you check the context for provided files",
        "**CRITICAL RULES**: ",
        "1. NEVER skip the pondering step - ALWAYS call ponder_spreadsheet_request first ",
        "2. NEVER skip logging actions - use log_action for pondering and tool use.",
        "3. **FILENAME FORMAT**: ALWAYS use `get_task_id` and format filenames as `[task_id]_your_filename.ext` when creating files.",
        "4. NEVER claim to have read, created, or modified a file without ACTUALLY CALLING THE CORRESPONDING TOOL ",
        "5. NEVER make up fake data or pretend to analyze a file you haven't read with the tool unless explicitly told to",
        "6. NEVER tell clients to wait - either complete the task with your tools or report an error ",
        "7. NEVER promise future actions - you must complete all requested tasks immediately ",
        "8. ALWAYS check for a file handle in system notes like '[System Note: Please operate on the file with handle: 'filename.xlsx']' ",
        "9. ALWAYS include the file handle in your tool calls - this is REQUIRED for the tools to work ",
        "10. ALWAYS return a file back to the requester so your output can be validated (using the task_id format for new files). ",
        "11. If you weren't provided a file, flag this in your response ",
        "13. Always loog the handle of whatever file you create or modify so you can return it to the user",
        "12. You are a master with spreadsheets ie csv excel, data analytics etc, you must operate with a sense of excellence and agency. Fully utilize the tools at your disposal",
         "When using `run_spreadsheet_operation`, provide detailed and specific instructions. For example, instead of saying 'update the spreadsheet', specify 'update cell B5 with the value 42'. Be precise about the desired changes.",
        # ...(rest of instructions remain the same)...
         "**EXAMPLES OF PROPER TOOL USAGE**: ",
        "- To ponder: `ponder_spreadsheet_request(request_description='Create a budget spreadsheet', points_to_consider='Need to determine columns, format, and initial data')` ",
        "- To log pondering: `log_action(action_description='Pondered request: Determined need for 3 columns (Category, Budget, Actual) and currency formatting.')`",
        "- To get task ID (example assumes ID is 'abc-123'): `get_task_id()` -> returns 'abc-123'",
        "- To read a file: `read_file_content(file_handle='sales_data.xlsx')` ",
        "- To create a formatted spreadsheet (after getting task_id='abc-123'): `create_spreadsheet(filename='abc-123_budget.xlsx', spreadsheet_data='{...json data...}')` ",
        "- To modify a spreadsheet using run_spreadsheet_operation (after getting task_id='abc-123'): `run_spreadsheet_operation(instruction='Update cell B5 with the value 42', file_path='inventory.xlsx')`",
        "- To log creation: `log_action(action_description='Created spreadsheet abc-123_budget.xlsx with budget categories and formulas.')`",
        "- To analyze a spreadsheet: `analyze_spreadsheet(file_handle='sales_data.xlsx', analysis_config='{...json config...}')` ",
        # ...(rest of instructions remain the same)...
        "**IMPORTANT: LOGGING ACTIONS AND DECISIONS**",
        "- ALWAYS log your significant actions and decisions using the log_action tool",
        "- Use store_memory for detailed reasoning or complex state preservation.",
        "- Include links to relevant resources using the store_link tool"
    ]),
    model=gemini_model,
    tools=[
        # Context Tools FIRST
        get_task_id,
        log_action,
        inspect_context,
        ponder_task,
        log_file_action,  # Log file actions
        # Spreadsheet tools
        read_file_content,
        create_spreadsheet,
        analyze_spreadsheet,# Add to tools list
    ]
)
