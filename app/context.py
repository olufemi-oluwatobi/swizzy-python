from dataclasses import dataclass, field
from typing import List
import uuid
from logging import getLogger
from fastapi import FastAPI
from agents import Runner, RunContextWrapper, function_tool # Added RunContextWrapper, function_tool

logger = getLogger(__name__)

@dataclass
class TaskContext:
    """Context object to be passed through agent runs, holding task-specific info."""
    task_id: str
    action_log: List[str] = field(default_factory=list)


# --- Context Tools Definition ---

@function_tool
async def get_task_id(wrapper: RunContextWrapper[TaskContext]) -> str:
    """Returns the unique ID for the current task."""
    return wrapper.context.task_id

@function_tool
async def log_action(wrapper: RunContextWrapper[TaskContext], action_description: str) -> str:
    """Logs a description of an action performed by the agent into the task context."""
    wrapper.context.action_log.append(action_description)
    logger.info(f"[Task {wrapper.context.task_id}] Logged action: {action_description}")
    return f"Action logged: {action_description}"