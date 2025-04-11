import os
import logging
import io
import json
from typing import Dict, List, Any, Tuple, Optional
import pandas as pd
import openpyxl
from openpyxl import load_workbook
from openpyxl.utils import get_column_letter, column_index_from_string
from openpyxl.styles import Font, PatternFill, Alignment
from app.services import storage_service
from agents import function_tool

logger = logging.getLogger(__name__)

@function_tool
def ponder_spreadsheet_request(request_description: str, points_to_consider: str) -> str:
    """
    A tool for the spreadsheet agent to think through a request before taking action.
    This allows for more careful planning and consideration of the appropriate approach.
    
    Args:
        request_description: A brief description of the client's request
        points_to_consider: Key points to consider when handling this request
        
    Returns:
        Guidance on how to proceed with the request
    """
    print(f"Spreadsheet agent pondering request: {request_description}")
    print(f"Points to consider: {points_to_consider}")
    
    # For now, this just echoes back the points with some generic guidance
    response = {
        "analysis": points_to_consider,
        "recommendation": "Based on your analysis, proceed with the appropriate spreadsheet tool calls to fulfill the request. Remember to use read_file_content first if working with an existing spreadsheet, create_spreadsheet for new spreadsheets, or modify_spreadsheet to make changes to existing files."
    }
    
    return json.dumps(response)

def apply_cell_format(cell, format_spec):
    """Apply formatting to a cell based on the format specification."""
    # Font formatting
    if format_spec.get("bold"):
        if cell.font:
            cell.font = Font(bold=True, name=cell.font.name, size=cell.font.size)
        else:
            cell.font = Font(bold=True)
    
    # Background color
    if format_spec.get("bg_color"):
        # Ensure color is in aRGB format (8 characters with FF alpha channel)
        color = format_spec["bg_color"]
        # If it's a 6-character hex, add FF alpha channel prefix
        if len(color) == 6 and all(c in "0123456789ABCDEFabcdef" for c in color):
            color = "FF" + color
        # If it doesn't start with FF and is 6 chars, add the alpha
        elif len(color) == 6:
            color = "FF" + color
        cell.fill = PatternFill(start_color=color, end_color=color, fill_type="solid")
    
    # Number format
    if format_spec.get("number_format"):
        cell.number_format = format_spec["number_format"]
    
    # Alignment
    if format_spec.get("align"):
        align_type = format_spec["align"]
        if align_type == "center":
            cell.alignment = Alignment(horizontal="center")
        elif align_type == "right":
            cell.alignment = Alignment(horizontal="right")
        elif align_type == "left":
            cell.alignment = Alignment(horizontal="left")

@function_tool
def create_spreadsheet(filename: str, spreadsheet_data: str) -> str:
    """
    Creates a new spreadsheet file (.xlsx) with the given data, formulas, and formatting.

    Args:
        filename: The desired name for the spreadsheet file (including extension).
        spreadsheet_data: JSON string containing sheet data, formulas, and formatting. Format:
            {
                "sheets": [
                    {
                        "name": "Sheet1",
                        "data": [
                            ["Header1", "Header2", "Header3"],
                            ["Value1", 10, "=B2*2"],
                            ["Value2", 20, "=B3*2"]
                        ],
                        "column_widths": {"A": 15, "B": 10},
                        "formats": [
                            {"range": "A1:C1", "bold": true, "bg_color": "FFCCCCCC"},
                            {"range": "B2:B3", "number_format": "#,##0.00"}
                        ]
                    }
                ]
            }

    Returns:
        The file handle of the created file.
    """
    logger.info(f"Attempting to create spreadsheet '{filename}'.")
    # Ensure filename has a valid extension, default to .xlsx if not
    if not filename.lower().endswith('.xlsx'):
        logger.warning(f"Filename '{filename}' lacks .xlsx extension. Appending '.xlsx'.")
        filename += '.xlsx'

    try:
        print(f"Creating spreadsheet '{filename}' with advanced formatting")
        
        # Parse the JSON input
        try:
            spec = json.loads(spreadsheet_data)
        except json.JSONDecodeError:
            # Fallback to CSV format if JSON parsing fails
            print("JSON parsing failed, falling back to CSV format")
            csv_data_io = io.StringIO(spreadsheet_data)
            df = pd.read_csv(csv_data_io)
            
            # Create a workbook with the DataFrame
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Sheet1"
            
            # Write headers
            for col_idx, col_name in enumerate(df.columns, 1):
                ws.cell(row=1, column=col_idx, value=col_name).font = Font(bold=True)
                
            # Write data
            for row_idx, row in enumerate(df.values, 2):
                for col_idx, value in enumerate(row, 1):
                    ws.cell(row=row_idx, column=col_idx, value=value)
                    
            # Auto-adjust column widths
            for col in ws.columns:
                max_length = 0
                column = col[0].column_letter
                for cell in col:
                    if cell.value:
                        max_length = max(max_length, len(str(cell.value)))
                adjusted_width = (max_length + 2)
                ws.column_dimensions[column].width = adjusted_width
        else:
            # Process the JSON specification
            wb = openpyxl.Workbook()
            
            # Remove the default sheet
            default_sheet = wb.active
            wb.remove(default_sheet)
            
            # Process each sheet in the specification
            for sheet_idx, sheet_spec in enumerate(spec.get("sheets", [])):
                sheet_name = sheet_spec.get("name", f"Sheet{sheet_idx+1}")
                ws = wb.create_sheet(title=sheet_name)
                
                # Add data and formulas
                data = sheet_spec.get("data", [])
                for row_idx, row_data in enumerate(data, 1):
                    for col_idx, cell_value in enumerate(row_data, 1):
                        cell = ws.cell(row=row_idx, column=col_idx)
                        
                        # Handle formulas (starting with =)
                        if isinstance(cell_value, str) and cell_value.startswith('='):
                            cell.value = cell_value
                        else:
                            cell.value = cell_value
                
                # Set column widths
                for col_letter, width in sheet_spec.get("column_widths", {}).items():
                    ws.column_dimensions[col_letter].width = width
                
                # Apply formats
                for format_spec in sheet_spec.get("formats", []):
                    cell_range = format_spec.get("range")
                    if cell_range:
                        for cell in ws[cell_range]:
                            # Apply cell formatting
                            if isinstance(cell, tuple):
                                for c in cell:
                                    apply_cell_format(c, format_spec)
                            else:
                                apply_cell_format(cell, format_spec)
        
        # Save to bytes
        output_excel_io = io.BytesIO()
        wb.save(output_excel_io)
        excel_bytes = output_excel_io.getvalue()

        # Upload the file bytes using the storage service
        file_handle = storage_service.upload_file(filename, excel_bytes)
        logger.info(f"Successfully created spreadsheet '{filename}' with handle '{file_handle}'.")
        return file_handle

    except Exception as e:
        print(f"Error creating spreadsheet '{filename}': {e}")
        logger.exception(f"Error creating spreadsheet '{filename}': {e}")
        return f"Error creating spreadsheet '{filename}': {e}"

@function_tool
def modify_spreadsheet(file_handle: str, modifications: str) -> str:
    """
    Modifies an existing spreadsheet file identified by its handle.

    Args:
        file_handle: The handle of the spreadsheet file to modify.
        modifications: A JSON string containing a list of operations to perform on the spreadsheet.
          Example: [{"operation": "update_cell", "cell": "B5", "value": "42"}]
          
          Supported operations:
          - update_cell: Updates a single cell value
          - add_row: Adds a new row with the provided data
          - delete_row: Deletes a row at the specified index
          - clear_range: Clears all values in the specified range
          - set_formula: Sets a formula in the specified cell
          - apply_basic_style: Applies basic styling to a range of cells

    Returns:
        The file handle of the modified spreadsheet.
    """
    logger.info(f"Attempting to modify spreadsheet '{file_handle}'. Modifications: {modifications}")

    try:
        # 1. Download the existing file
        print(f"Downloading file '{file_handle}' for modification.")
        file_bytes = storage_service.download_file(file_handle)
        excel_io = io.BytesIO(file_bytes)

        # 2. Parse the JSON modifications string
        try:
            ops = json.loads(modifications)
            if not isinstance(ops, list):
                raise ValueError("Modifications JSON must be a list of operations.")
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in modifications for '{file_handle}': {e}")
            return f"Error: Invalid format for modifications - must be a valid JSON list. {e}"
        except ValueError as e:
             logger.error(f"Invalid JSON structure for '{file_handle}': {e}")
             return f"Error: {e}"

        # 3. Load the workbook using openpyxl
        try:
            wb = load_workbook(excel_io)
        except Exception as e:
             logger.exception(f"Error reading Excel file '{file_handle}' with openpyxl: {e}")
             return f"Error: Could not read the Excel file '{file_handle}'. Is it a valid .xlsx file? {e}"

        # 4. Apply operations using openpyxl
        sheet_names = wb.sheetnames
        if not sheet_names:
             return f"Error: Excel file '{file_handle}' appears to be empty or has no sheets."

        for op in ops:
            if not isinstance(op, dict) or 'operation' not in op:
                logger.warning(f"Skipping invalid operation item: {op}")
                continue

            op_type = op['operation']
            # Default to first sheet if not specified
            sheet_name = op.get('sheet', sheet_names[0]) 

            if sheet_name not in wb:
                logger.error(f"Sheet '{sheet_name}' not found in '{file_handle}'. Available: {sheet_names}")
                return f"Error: Sheet '{sheet_name}' not found in the spreadsheet."
            
            ws = wb[sheet_name] # Get the openpyxl worksheet

            try:
                # --- Reimplementing operations using openpyxl --- 
                if op_type == 'update_cell':
                    cell = op['cell']
                    value = op['value']
                    ws[cell] = value # Direct assignment
                    logger.info(f"Updated cell {cell} in sheet '{sheet_name}' to '{value}'.")

                elif op_type == 'add_row':
                    data = op['data']
                    ws.append(data) # Append row
                    logger.info(f"Added row {data} to sheet '{sheet_name}'.")

                elif op_type == 'delete_row':
                    # openpyxl row indices are 1-based
                    row_index_0based = op['row_index'] 
                    if not isinstance(row_index_0based, int) or row_index_0based < 0:
                        raise ValueError("row_index must be a non-negative integer.")
                    ws.delete_rows(row_index_0based + 1, 1)
                    logger.info(f"Deleted row at 0-based index {row_index_0based} from sheet '{sheet_name}'.")

                elif op_type == 'clear_range':
                    range_str = op['range']
                    for row in ws[range_str]:
                        for cell in row:
                            cell.value = None # Clear cell value
                    logger.info(f"Cleared range {range_str} in sheet '{sheet_name}'.")

                # --- New Operations ---
                elif op_type == 'set_formula':
                    cell = op['cell']
                    formula = op['formula']
                    if not formula.startswith('='):
                        formula = '=' + formula # Ensure it's treated as a formula
                    ws[cell] = formula
                    logger.info(f"Set formula in cell {cell} of sheet '{sheet_name}' to '{formula}'.")

                elif op_type == 'apply_basic_style':
                    range_str = op['range']
                    style_dict = op.get('style', {})
                    is_bold = style_dict.get('bold', False)
                    bg_color = style_dict.get('bg_color')
                    number_format = style_dict.get('number_format')
                    
                    for row in ws[range_str]:
                        for cell in row:
                            if is_bold:
                                cell.font = Font(bold=True)
                            if bg_color:
                                # Ensure color is in aRGB format (8 characters with FF alpha channel)
                                color = bg_color
                                if len(color) == 6 and all(c in "0123456789ABCDEFabcdef" for c in color):
                                    color = "FF" + color
                                cell.fill = PatternFill(start_color=color, end_color=color, fill_type="solid")
                            if number_format:
                                cell.number_format = number_format
                                
                    logger.info(f"Applied style to range {range_str} in sheet '{sheet_name}'.")
                
                else:
                    logger.warning(f"Unsupported operation type '{op_type}' specified.")
                    return f"Error: Unsupported operation type '{op_type}'."

            except KeyError as e:
                logger.error(f"Missing required key for operation '{op_type}': {e}")
                return f"Error: Missing data for operation '{op_type}': {e}."
            except Exception as e:
                logger.exception(f"Error processing operation '{op_type}' on sheet '{sheet_name}': {e}")
                return f"Unexpected error during operation '{op_type}' on sheet '{sheet_name}': {e}"

        # 5. Save the modified workbook
        output_excel_io = io.BytesIO()
        wb.save(output_excel_io)
        excel_bytes = output_excel_io.getvalue()

        # Upload the modified file
        # Use the same file handle to replace the original file
        storage_service.upload_file(file_handle, excel_bytes)
        logger.info(f"Successfully modified and saved spreadsheet '{file_handle}'.")
        return file_handle
    
    except FileNotFoundError:
        logger.error(f"Could not find file with handle '{file_handle}' for modification.")
        return f"Error: File not found: {file_handle}"
    except Exception as e:
        logger.exception(f"Error modifying spreadsheet '{file_handle}': {e}")
        return f"Error modifying spreadsheet: {e}"
