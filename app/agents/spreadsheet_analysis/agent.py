from __future__ import annotations

import logging
from agents import Agent
from app.context import TaskContext
from app.agents.model_config import gemini_model
from app.tools.spreadsheet_tools import smart_spreadsheet_analysis

logger = logging.getLogger(__name__)

spreadsheet_analysis_agent = Agent[TaskContext](
    name="Spreadsheet Analysis Specialist",
    instructions="""You are a specialized agent for in-depth spreadsheet analysis.
    You must:
    1. Use smart_spreadsheet_analysis for deep data analysis
    2. Provide detailed explanations of findings
    3. Generate clear, well-formatted reports
    4. Handle various types of data appropriately
    """,
    model=gemini_model,
    tools=[smart_spreadsheet_analysis]
)
