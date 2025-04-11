"""
Utility functions for validating task outcomes against plans and success criteria.
"""
import logging
import json
import time
from typing import Dict, List, Any, Optional
from app.services.gemini_service import GeminiService
from app.tools.memory_utils import log_agent_action
from app.tools.memory_tools import store_memory

logger = logging.getLogger(__name__)

def validate_task_with_gemini(
    plan: Dict[str, Any],
    outcomes: Dict[str, Any],
    agent_name: str = "Validator Agent"
) -> Dict[str, Any]:
    """
    Validates task completion against success criteria using Google Gemini.
    
    Args:
        plan: The original plan dictionary
        outcomes: Dictionary describing the task outcomes
        agent_name: Name of the agent performing validation
        
    Returns:
        Dictionary containing the validation results
    """
    logger.info(f"Validating task completion for plan: {plan.get('plan_id', 'unknown')}")
    
    try:
        # Initialize Gemini service
        gemini_service = GeminiService()
        
        # Extract relevant information from the plan
        plan_id = plan.get("plan_id", "unknown")
        task_description = plan.get("task_description", "unknown")
        success_criteria = plan.get("success_criteria", [])
        
        # Create a prompt for validation
        prompt = f"""
        Validate the following task outcomes against the success criteria:
        
        TASK: {task_description}
        
        PLAN ID: {plan_id}
        
        SUCCESS CRITERIA:
        {json.dumps(success_criteria, indent=2)}
        
        OUTCOMES:
        {json.dumps(outcomes, indent=2)}
        
        Please provide a detailed validation in JSON format with the following structure:
        {{
            "plan_id": "{plan_id}",
            "task_description": "{task_description}",
            "validation_time": [current timestamp],
            "criteria_met": [
                "List of criteria that were fully met"
            ],
            "criteria_partially_met": [
                {{
                    "criterion": "The criterion text",
                    "reason": "Explanation of why it was only partially met",
                    "completion_percentage": X  // A number between 0 and 100
                }}
            ],
            "criteria_not_met": [
                {{
                    "criterion": "The criterion text",
                    "reason": "Explanation of why it was not met"
                }}
            ],
            "overall_success": true/false,  // Based on whether all critical criteria were met
            "completion_percentage": X,  // Overall completion percentage (0-100)
            "recommendations": [
                "Specific recommendation 1",
                "Specific recommendation 2"
            ]
        }}
        
        Be objective and evidence-based in your assessment. If a criterion is vague, interpret it reasonably.
        """
        
        # Use Gemini to perform the validation
        result = gemini_service.analyze_image(b"", prompt)  # Using empty bytes as we're just using text
        
        if result.get("success"):
            # Try to parse JSON from the response
            text = result["text"]
            json_start = text.find('{')
            json_end = text.rfind('}')
            
            if json_start >= 0 and json_end > json_start:
                json_str = text[json_start:json_end+1]
                
                # Parse the JSON to validate it
                validation = json.loads(json_str)
                
                # Ensure all required fields are present
                if "plan_id" not in validation:
                    validation["plan_id"] = plan_id
                if "task_description" not in validation:
                    validation["task_description"] = task_description
                if "validation_time" not in validation:
                    validation["validation_time"] = time.time()
                
                # Log the validation
                log_agent_action(
                    agent_name=agent_name,
                    action_type="task_validation",
                    action_details={
                        "plan_id": plan_id,
                        "task_description": task_description,
                        "completion_percentage": validation.get("completion_percentage", 0),
                        "overall_success": validation.get("overall_success", False)
                    },
                    outcome=f"Validated task completion: {validation.get('overall_success', False)}",
                    tags=["validation", "task_completion", task_description.lower().replace(" ", "_")[:20]]
                )
                
                # Store the validation in memory
                memory_id = store_memory(
                    f"Validation for: {task_description}",
                    {
                        "validation": validation,
                        "created_at": time.time(),
                        "plan_id": plan_id
                    },
                    ["validation", "task_completion", task_description.lower().replace(" ", "_")[:20]]
                )
                
                # Add memory ID to the validation
                validation["memory_id"] = memory_id
                
                return validation
            else:
                # If no valid JSON found, create a default validation
                return _create_default_validation(plan, outcomes, "Failed to parse Gemini response")
        else:
            # If Gemini fails, create a default validation
            error_message = result.get("error", "Unknown error")
            logger.error(f"Error validating with Gemini: {error_message}")
            return _create_default_validation(plan, outcomes, f"Gemini error: {error_message}")
        
    except Exception as e:
        logger.exception(f"Error validating task completion: {e}")
        return _create_default_validation(plan, outcomes, str(e))

def _create_default_validation(
    plan: Dict[str, Any], 
    outcomes: Dict[str, Any], 
    error: str = "Unknown error"
) -> Dict[str, Any]:
    """
    Creates a default validation when Gemini fails.
    
    Args:
        plan: The original plan dictionary
        outcomes: Dictionary describing the task outcomes
        error: Error message
        
    Returns:
        Dictionary containing the default validation
    """
    plan_id = plan.get("plan_id", "unknown")
    task_description = plan.get("task_description", "unknown")
    
    # Create a basic validation structure
    validation = {
        "plan_id": plan_id,
        "task_description": task_description,
        "validation_time": time.time(),
        "error": error,
        "criteria_met": [],
        "criteria_partially_met": [],
        "criteria_not_met": [],
        "overall_success": False,
        "completion_percentage": 0,
        "recommendations": [
            "Validation failed due to technical error",
            "Please retry the validation"
        ]
    }
    
    # Log the default validation
    log_agent_action(
        agent_name="Validator Agent",
        action_type="default_validation",
        action_details={
            "plan_id": plan_id,
            "task_description": task_description,
            "error": error
        },
        outcome=f"Created default validation due to error: {error}",
        tags=["validation", "default_validation", "error", task_description.lower().replace(" ", "_")[:20]]
    )
    
    # Store the validation in memory
    memory_id = store_memory(
        f"Default validation for: {task_description}",
        {
            "validation": validation,
            "created_at": time.time(),
            "plan_id": plan_id,
            "is_default": True,
            "error": error
        },
        ["validation", "default_validation", "error", task_description.lower().replace(" ", "_")[:20]]
    )
    
    # Add memory ID to the validation
    validation["memory_id"] = memory_id
    
    return validation

def compare_validations(
    previous_validation: Dict[str, Any],
    current_validation: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Compares two validations to track progress.
    
    Args:
        previous_validation: The previous validation results
        current_validation: The current validation results
        
    Returns:
        Dictionary containing the comparison results
    """
    logger.info(f"Comparing validations for plan: {current_validation.get('plan_id', 'unknown')}")
    
    try:
        # Extract relevant information
        plan_id = current_validation.get("plan_id", "unknown")
        task_description = current_validation.get("task_description", "unknown")
        
        # Calculate differences
        prev_completion = previous_validation.get("completion_percentage", 0)
        current_completion = current_validation.get("completion_percentage", 0)
        completion_change = current_completion - prev_completion
        
        prev_criteria_met = set(previous_validation.get("criteria_met", []))
        current_criteria_met = set(current_validation.get("criteria_met", []))
        
        newly_met_criteria = list(current_criteria_met - prev_criteria_met)
        no_longer_met_criteria = list(prev_criteria_met - current_criteria_met)
        
        # Create comparison results
        comparison = {
            "plan_id": plan_id,
            "task_description": task_description,
            "comparison_time": time.time(),
            "previous_validation_time": previous_validation.get("validation_time"),
            "current_validation_time": current_validation.get("validation_time"),
            "previous_completion": prev_completion,
            "current_completion": current_completion,
            "completion_change": completion_change,
            "newly_met_criteria": newly_met_criteria,
            "no_longer_met_criteria": no_longer_met_criteria,
            "progress_trend": "improving" if completion_change > 0 else "declining" if completion_change < 0 else "stable",
            "recommendations": []
        }
        
        # Generate recommendations based on the comparison
        if completion_change > 0:
            comparison["recommendations"].append(f"Continue the current approach, showing {completion_change}% improvement")
        elif completion_change < 0:
            comparison["recommendations"].append(f"Review recent changes as completion has decreased by {abs(completion_change)}%")
        else:
            comparison["recommendations"].append("No change in completion percentage, consider new approaches")
            
        if newly_met_criteria:
            comparison["recommendations"].append(f"Successfully addressed {len(newly_met_criteria)} previously unmet criteria")
            
        if no_longer_met_criteria:
            comparison["recommendations"].append(f"Urgent: {len(no_longer_met_criteria)} previously met criteria are no longer satisfied")
        
        # Log the comparison
        log_agent_action(
            agent_name="Validator Agent",
            action_type="validation_comparison",
            action_details={
                "plan_id": plan_id,
                "task_description": task_description,
                "completion_change": completion_change,
                "progress_trend": comparison["progress_trend"]
            },
            outcome=f"Compared validations: {comparison['progress_trend']} trend",
            tags=["validation", "comparison", task_description.lower().replace(" ", "_")[:20]]
        )
        
        # Store the comparison in memory
        memory_id = store_memory(
            f"Validation comparison for: {task_description}",
            {
                "comparison": comparison,
                "created_at": time.time(),
                "plan_id": plan_id
            },
            ["validation", "comparison", task_description.lower().replace(" ", "_")[:20]]
        )
        
        # Add memory ID to the comparison
        comparison["memory_id"] = memory_id
        
        return comparison
        
    except Exception as e:
        logger.exception(f"Error comparing validations: {e}")
        
        # Create a basic comparison result
        comparison = {
            "plan_id": current_validation.get("plan_id", "unknown"),
            "task_description": current_validation.get("task_description", "unknown"),
            "comparison_time": time.time(),
            "error": str(e),
            "recommendations": ["Comparison failed due to error, please retry"]
        }
        
        # Log the error
        log_agent_action(
            agent_name="Validator Agent",
            action_type="comparison_error",
            action_details={
                "plan_id": current_validation.get("plan_id", "unknown"),
                "task_description": current_validation.get("task_description", "unknown"),
                "error": str(e)
            },
            outcome=f"Error comparing validations: {e}",
            tags=["validation", "comparison", "error", current_validation.get("task_description", "unknown").lower().replace(" ", "_")[:20]]
        )
        
        return comparison
