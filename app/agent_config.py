from __future__ import annotations

import os
import logging
from typing import List, Optional

from pydantic import BaseModel, Field
from openai import AsyncOpenAI
from dotenv import load_dotenv

from agents import OpenAIChatCompletionsModel

from app.agents import memory_agent_config, spreadsheet_agent, document_agent, research_agent, planner_agent, validator_agent, swizzy_assistant_agent

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

# Instruction Snippets
STYLE_INSTRUCTIONS = "Format your response clearly using markdown."

# --- Define Output Model ---
class SwizzyOutput(BaseModel):
    reasoning: str = Field(description="Brief reasoning for the chosen action (tool use or handoff).")
    action_taken: str = Field(description="Description of the action performed (e.g., 'Used read_file_content', 'Handed off to spreadsheet_agent', 'Executed analysis script').")
    outcome: str = Field(description="Summary of the outcome (e.g., 'Success', 'Completed analysis', 'Error occurred', 'Handoff initiated').")
    response_to_user: str = Field(description="The final message to convey to the user.")
    generated_handles: Optional[List[str]] = Field(default=None, description="List of new file handles generated by a specialist agent, if any.")
    error_details: Optional[str] = Field(default=None, description="Details of any error encountered during tool use or handoff, if applicable.")
    task_context_id: Optional[str] = Field(default=None, description="Unique ID for the current task context, if available.")

# The agent that starts the interaction is now the orchestrator
starting_agent = swizzy_assistant_agent