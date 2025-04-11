from agents import function_tool
from typing import Dict, Any

@function_tool
async def ponder_task(task_description: str, agent_name: str, current_reasoning: str ) -> Dict[str, Any]:
    """
    Analyzes the task and determines the best approach using available tools.
    
    Args:
        task_description: The task to analyze
        agent_name: Name of the agent doing the pondering
        current_reasoning: The reasoning you have done so far and what steps you have considered to take, annd tools  you have considered to utilize and any concerns you have about the task.
        
    Returns:
        Dict containing analysis and recommended approach
    """
    print(f"Agent {agent_name} is pondering the task: {task_description}", current_reasoning)
    return {
        "agent": agent_name,
        "task_analyzed": task_description,
        "reasoning": current_reasoning,
        "should_use_tools": True,  # For now, always try tools first
        "recommended_approach": "Use available tools to attempt task completion before requesting help",
        "memory_tag": f"{agent_name.lower()}_task_analysis"
    }
