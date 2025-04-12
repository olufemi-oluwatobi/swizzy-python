import os
import logging
import json
from typing import Dict, Any
from ..services.storage_service import storage_service
from ..services.gemini_service import GeminiService
from ..services.script_execution_service import ScriptExecutionService
from .spreadsheet_tools import analyze_spreadsheet
from agents import function_tool

logger = logging.getLogger(__name__)

@function_tool
def magic_analyze(file_handle: str, instructions: str) -> Dict[str, Any]:
    """
    Performs intelligent analysis on any document with AI-guided processing.
    
    Args:
        file_handle: The handle of the file to analyze
        instructions: Analysis requirements and guidancess
    
    Returns:
        Dictionary containing analysis results and report handles
    """
    try:
        gemini = GeminiService()
        script_executor = ScriptExecutionService()
        
        # Initial document analysis prompt
        analysis_prompt = f"""Analyze this document and provide analysis instructions:
        
        Instructions from user: {instructions}

        Analyze and determine:
        1. What type of analysis is needed
        2. What data processing steps are required
        3. What insights we should look for
        4. What type of outputs to generate

        Return a structured analysis plan in this format:
        {{
            "file_type": "type of file and processing needed",
            "analysis_needs": ["list of analyses needed"],
            "processing_steps": ["ordered list of steps"],
            "required_outputs": ["list of outputs to generate"],
            "script_needed": boolean,
            "script_instructions": "instructions in plain text if script needed"
        }}
        """
        # Get initial analysis
        result = gemini.analyze_text(analysis_prompt, "Document Analysis Plan")
        if not result.get("success"):
            raise Exception("Failed to generate analysis plan")

        analysis_plan = json.loads(result["text"])
        
        outputs = []
        analysis_results = {}
        
        # Execute analysis based on plan
        if analysis_plan.get("script_needed"):
            # Generate script if needed
            script_result = script_executor.generate_script(
                analysis_plan["script_instructions"],
                {"input_handle": file_handle},
                {"format": "json"}
            )
            
            # Execute script
            execution_result = script_executor.execute_script(
                script_result,
                {"input_handle": file_handle}
            )
            
            if execution_result.get("success"):
                outputs.extend(execution_result["output"].get("output_files", []))
                analysis_results["script_results"] = execution_result["output"]
        
        # Run standard analysis if specified
        if "spreadsheet_analysis" in analysis_plan.get("analysis_needs", []):
            spreadsheet_result = analyze_spreadsheet(
                file_handle,
                json.dumps({
                    "operations": [
                        {"type": "summary_stats", "metrics": ["mean", "median", "sum"]},
                        {"type": "trend_analysis"},
                        {"type": "correlation"}
                    ]
                })
            )
            analysis_results["spreadsheet_analysis"] = json.loads(spreadsheet_result)
        
        # Generate comprehensive report
        report_prompt = f"""Create a comprehensive analysis report:

        Analysis Plan: {json.dumps(analysis_plan, indent=2)}
        Analysis Results: {json.dumps(analysis_results, indent=2)}
        Generated Outputs: {json.dumps(outputs, indent=2)}

        Create a full report in Markdown format that:
        1. Summarizes the analysis performed
        2. Explains key findings
        3. Provides data insights
        4. Lists recommendations
        5. Includes links to generated files
        """
                
        report_result = gemini.analyze_text(report_prompt, "Generate Analysis Report")
        if not report_result.get("success"):
            raise Exception("Failed to generate report")
            
        # Save full report as MD file
        report_handle = storage_service.upload_file(
            "analysis_report.md",
            report_result["text"].encode('utf-8')
        )
        
        # Generate executive summary
        summary_prompt = f"""Create a brief executive summary of this analysis:
        {report_result["text"]}

        Focus on:
        1. Key findings
        2. Main insights
        3. Critical recommendations
        Maximum 3 paragraphs.
        """
        
        summary_result = gemini.analyze_text(summary_prompt, "Generate Summary")
        if not summary_result.get("success"):
            raise Exception("Failed to generate summary")
        
        return {
            "success": True,
            "summary": summary_result["text"],
            "report_handle": report_handle,
            "output_files": outputs,
            "analysis_results": analysis_results
        }
        
    except Exception as e:
        logger.exception(f"Magic analysis failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }
