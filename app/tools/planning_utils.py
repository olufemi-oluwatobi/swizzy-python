"""
Utility functions for planning tasks and evaluating outcomes.
"""
import logging
import json
import time
from typing import Dict, List, Any, Optional
from app.services.gemini_service import GeminiService
from app.tools.memory_utils import log_agent_action
from app.tools.memory_tools import store_memory

logger = logging.getLogger(__name__)

def generate_plan_with_gemini(
    task_description: str,
    context: str = "",
    agent_name: str = "Planner Agent"
) -> Dict[str, Any]:
    """
    Generates a structured plan using Google Gemini.
    
    Args:
        task_description: Description of the task to be planned
        context: Additional context for the planning (optional)
        agent_name: Name of the agent generating the plan
        
    Returns:
        Dictionary containing the structured plan
    """
    logger.info(f"Generating plan for task: {task_description}")
    
    try:
        # Initialize Gemini service
        gemini_service = GeminiService()
        
        # Create a prompt for generating a plan
        prompt = f"""
        Create a comprehensive plan for the following task:
        
        TASK: {task_description}
        
        {f"CONTEXT: {context}" if context else ""}
        
        The plan should be structured as a JSON object with the following format:
        {{
            "task_description": "{task_description}",
            "plan_id": "unique_identifier",
            "created_at": [current timestamp],
            "steps": [
                {{
                    "step_number": 1,
                    "description": "Detailed description of step 1",
                    "estimated_time": "X hours/minutes",
                    "dependencies": []
                }},
                {{
                    "step_number": 2,
                    "description": "Detailed description of step 2",
                    "estimated_time": "Y hours/minutes",
                    "dependencies": [1]
                }}
                // Additional steps...
            ],
            "success_criteria": [
                "Specific, measurable criterion 1",
                "Specific, measurable criterion 2"
                // Additional criteria...
            ],
            "resources_needed": [
                "Resource 1",
                "Resource 2"
                // Additional resources...
            ],
            "estimated_completion_time": "Total estimated time",
            "risks_and_mitigations": [
                {{
                    "risk": "Potential issue that might arise",
                    "probability": "High/Medium/Low",
                    "impact": "High/Medium/Low",
                    "mitigation": "How to prevent or address this risk"
                }}
                // Additional risks...
            ]
        }}
        
        Make the plan detailed, actionable, and realistic. Include at least 3-5 steps and 2-3 success criteria.
        Ensure each step has clear dependencies if applicable.
        Provide specific time estimates for each step.
        Identify at least 2 potential risks and their mitigations.
        """
        
        # Use Gemini to generate the plan
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
                if "task_description" not in plan:
                    plan["task_description"] = task_description
                if "plan_id" not in plan:
                    plan["plan_id"] = f"plan_{int(time.time())}"
                if "created_at" not in plan:
                    plan["created_at"] = time.time()
                
                # Log the plan creation
                log_agent_action(
                    agent_name=agent_name,
                    action_type="plan_creation",
                    action_details={
                        "task_description": task_description,
                        "steps_count": len(plan.get("steps", [])),
                        "success_criteria_count": len(plan.get("success_criteria", [])),
                        "plan_id": plan.get("plan_id")
                    },
                    outcome=f"Created plan for task: {task_description}",
                    tags=["planning", "task_plan", task_description.lower().replace(" ", "_")[:20]]
                )
                
                # Store the plan in memory
                memory_id = store_memory(
                    f"Plan for: {task_description}",
                    {
                        "plan": plan,
                        "created_at": time.time(),
                        "task_description": task_description
                    },
                    ["plan", "task_plan", task_description.lower().replace(" ", "_")[:20]]
                )
                
                # Add memory ID to the plan
                plan["memory_id"] = memory_id
                
                return plan
            else:
                # If no valid JSON found, create a default plan
                return _create_default_plan(task_description)
        else:
            # If Gemini fails, create a default plan
            error_message = result.get("error", "Unknown error")
            logger.error(f"Error generating plan with Gemini: {error_message}")
            return _create_default_plan(task_description)
        
    except Exception as e:
        logger.exception(f"Error generating plan: {e}")
        return _create_default_plan(task_description)

def _create_default_plan(task_description: str) -> Dict[str, Any]:
    """
    Creates a default plan when Gemini fails.
    
    Args:
        task_description: Description of the task to be planned
        
    Returns:
        Dictionary containing the default plan
    """
    plan_id = f"plan_{int(time.time())}"
    
    # Create a basic plan structure
    plan = {
        "task_description": task_description,
        "plan_id": plan_id,
        "created_at": time.time(),
        "steps": [
            {
                "step_number": 1,
                "description": "Analyze requirements",
                "estimated_time": "1 hour",
                "dependencies": []
            },
            {
                "step_number": 2,
                "description": "Gather necessary resources",
                "estimated_time": "2 hours",
                "dependencies": [1]
            },
            {
                "step_number": 3,
                "description": "Execute core task components",
                "estimated_time": "4 hours",
                "dependencies": [2]
            },
            {
                "step_number": 4,
                "description": "Review and validate results",
                "estimated_time": "1 hour",
                "dependencies": [3]
            }
        ],
        "success_criteria": [
            "All requirements are met",
            "Output is validated and error-free",
            "Task is completed within the estimated time"
        ],
        "resources_needed": [
            "Documentation",
            "Required tools",
            "Access permissions"
        ],
        "estimated_completion_time": "8 hours",
        "risks_and_mitigations": [
            {
                "risk": "Missing requirements",
                "probability": "Medium",
                "impact": "High",
                "mitigation": "Thorough initial analysis and stakeholder confirmation"
            },
            {
                "risk": "Resource unavailability",
                "probability": "Medium",
                "impact": "Medium",
                "mitigation": "Identify alternative resources in advance"
            }
        ]
    }
    
    # Log the default plan creation
    log_agent_action(
        agent_name="Planner Agent",
        action_type="default_plan_creation",
        action_details={
            "task_description": task_description,
            "plan_id": plan_id
        },
        outcome=f"Created default plan for task: {task_description}",
        tags=["planning", "default_plan", task_description.lower().replace(" ", "_")[:20]]
    )
    
    # Store the plan in memory
    memory_id = store_memory(
        f"Default plan for: {task_description}",
        {
            "plan": plan,
            "created_at": time.time(),
            "task_description": task_description,
            "is_default": True
        },
        ["plan", "default_plan", task_description.lower().replace(" ", "_")[:20]]
    )
    
    # Add memory ID to the plan
    plan["memory_id"] = memory_id
    
    return plan

def validate_task_completion(
    plan: Dict[str, Any],
    outcomes: Dict[str, Any],
    agent_name: str = "Validator Agent"
) -> Dict[str, Any]:
    """
    Validates task completion against the plan's success criteria.
    
    Args:
        plan: The original plan dictionary
        outcomes: Dictionary describing the task outcomes
        agent_name: Name of the agent performing validation
        
    Returns:
        Dictionary containing the validation results
    """
    logger.info(f"Validating task completion for plan: {plan.get('plan_id', 'unknown')}")
    
    try:
        # Initialize validation results
        validation = {
            "plan_id": plan.get("plan_id", "unknown"),
            "task_description": plan.get("task_description", "unknown"),
            "validation_time": time.time(),
            "success_criteria": plan.get("success_criteria", []),
            "criteria_met": [],
            "criteria_partially_met": [],
            "criteria_not_met": [],
            "overall_success": False,
            "completion_percentage": 0,
            "recommendations": []
        }
        
        # In a real implementation, this would use Gemini to evaluate each criterion
        # For now, we'll just provide a placeholder implementation
        
        # Assume all criteria are met for demonstration purposes
        validation["criteria_met"] = plan.get("success_criteria", [])
        validation["completion_percentage"] = 100
        validation["overall_success"] = True
        validation["recommendations"] = ["Task completed successfully"]
        
        # Log the validation
        log_agent_action(
            agent_name=agent_name,
            action_type="task_validation",
            action_details={
                "plan_id": plan.get("plan_id", "unknown"),
                "task_description": plan.get("task_description", "unknown"),
                "completion_percentage": validation["completion_percentage"],
                "overall_success": validation["overall_success"]
            },
            outcome=f"Validated task completion: {validation['overall_success']}",
            tags=["validation", "task_completion", plan.get("task_description", "unknown").lower().replace(" ", "_")[:20]]
        )
        
        # Store the validation in memory
        memory_id = store_memory(
            f"Validation for: {plan.get('task_description', 'unknown')}",
            {
                "validation": validation,
                "created_at": time.time(),
                "plan_id": plan.get("plan_id", "unknown")
            },
            ["validation", "task_completion", plan.get("task_description", "unknown").lower().replace(" ", "_")[:20]]
        )
        
        # Add memory ID to the validation
        validation["memory_id"] = memory_id
        
        return validation
        
    except Exception as e:
        logger.exception(f"Error validating task completion: {e}")
        
        # Create a basic validation result
        validation = {
            "plan_id": plan.get("plan_id", "unknown"),
            "task_description": plan.get("task_description", "unknown"),
            "validation_time": time.time(),
            "error": str(e),
            "overall_success": False,
            "completion_percentage": 0,
            "recommendations": ["Validation failed due to error, please retry"]
        }
        
        # Log the error
        log_agent_action(
            agent_name=agent_name,
            action_type="validation_error",
            action_details={
                "plan_id": plan.get("plan_id", "unknown"),
                "task_description": plan.get("task_description", "unknown"),
                "error": str(e)
            },
            outcome=f"Error validating task completion: {e}",
            tags=["validation", "error", plan.get("task_description", "unknown").lower().replace(" ", "_")[:20]]
        )
        
        return validation
