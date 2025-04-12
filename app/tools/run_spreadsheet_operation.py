from typing import List, Dict
from app.services.script_execution_service import ScriptExecutionService
from app.tools.data_extraction_tools import extract_spreadsheet_data


def run_spreadsheet_operation(instruction: str, file_path: str) -> str:
    """
    Executes a custom operation on a spreadsheet based on the given instruction.

    Args:
        instruction: The instruction to be performed on the file.
        file_path: The path to the file to be processed.

    Returns:
        The output of the script execution.
    """

    # 1. Extract data and metadata about the Excel file
    spreadsheet_data = extract_spreadsheet_data(file_path)

    # 2. Generate a script based on the instruction and spreadsheet_data
    script_execution_service = ScriptExecutionService()
    script = script_execution_service.generate_script(instruction, {"file_path": file_path, "spreadsheet_data": spreadsheet_data}, {})

    # 3. Execute the script using the script executor, passing in the spreadsheet data
    output = script_execution_service.execute_script(script, {"file_path": file_path, "spreadsheet_data": spreadsheet_data})

    return output