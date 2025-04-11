"""
Tools for extracting structured data from documents and converting between formats.
"""
import os
import logging
import json
import io
import re
from typing import Dict, List, Any, Optional, Union
import pandas as pd
from app.services import storage_service
from app.services.gemini_service import GeminiService
from app.tools.content_tools import extract_pdf_content_with_formatting
from app.tools.memory_utils import log_data_extraction, log_agent_action
from agents import function_tool

logger = logging.getLogger(__name__)

@function_tool
def extract_structured_data(file_handle: str, data_type: str = "invoice") -> str:
    """
    Extracts structured data from a document (PDF or image) using AI.
    
    Args:
        file_handle: The handle of the file to extract from
        data_type: Type of data to extract - 'invoice', 'receipt', 'table', etc.
        
    Returns:
        JSON string containing the extracted structured data
    """
    logger.info(f"Extracting {data_type} data from: {file_handle}")
    
    try:
        # Get the file bytes
        file_bytes = storage_service.download_file(file_handle)
        
        # Determine file type based on extension
        file_extension = os.path.splitext(file_handle)[1].lower()
        
        # Extract data based on file type
        if file_extension in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp']:
            # For images, use Gemini service
            gemini_service = GeminiService()
            result = gemini_service.extract_structured_data(file_bytes, data_type)
            
            if result.get("success"):
                # Log the successful extraction
                extraction_details = {
                    "file_type": "image",
                    "extraction_type": data_type,
                    "file_extension": file_extension,
                    "summary": f"Successfully extracted {data_type} data from image"
                }
                log_data_extraction(
                    file_handle=file_handle,
                    extraction_type=data_type,
                    extraction_details=extraction_details,
                    tags=["extraction", data_type, "image"]
                )
                
                return json.dumps(result["structured_data"], indent=2)
            else:
                error_message = result.get("error", "Unknown error")
                logger.error(f"Error extracting data from image: {error_message}")
                
                # Log the failed extraction
                extraction_details = {
                    "file_type": "image",
                    "extraction_type": data_type,
                    "file_extension": file_extension,
                    "error": error_message
                }
                log_data_extraction(
                    file_handle=file_handle,
                    extraction_type=data_type,
                    extraction_details=extraction_details,
                    tags=["extraction_error", data_type, "image"]
                )
                
                return json.dumps({"error": error_message})
                
        elif file_extension == '.pdf':
            # For PDFs, first convert to text with formatting
            markdown_content = extract_pdf_content_with_formatting(file_bytes)
            
            # Then use Gemini to extract structured data
            gemini_service = GeminiService()
            
            # Create a prompt for structured data extraction
            prompt = f"""
            Extract structured data from this {data_type} in PDF format.
            The content has been converted to Markdown format.
            Please extract all relevant fields and return them in a clean JSON format.
            
            {markdown_content[:10000]}  # Limit content length to avoid token limits
            """
            
            # Use Gemini to extract structured data
            result = gemini_service.analyze_image(file_bytes, prompt)
            
            if result.get("success"):
                # Try to parse any JSON in the response text
                try:
                    # Look for JSON-like content in the text
                    text = result["text"]
                    json_start = text.find('{')
                    json_end = text.rfind('}')
                    
                    if json_start >= 0 and json_end > json_start:
                        json_str = text[json_start:json_end+1]
                        structured_data = json.loads(json_str)
                        
                        # Log the successful extraction
                        extraction_details = {
                            "file_type": "pdf",
                            "extraction_type": data_type,
                            "fields_extracted": list(structured_data.keys()),
                            "summary": f"Successfully extracted {data_type} data from PDF"
                        }
                        log_data_extraction(
                            file_handle=file_handle,
                            extraction_type=data_type,
                            extraction_details=extraction_details,
                            tags=["extraction", data_type, "pdf"]
                        )
                        
                        return json.dumps(structured_data, indent=2)
                    else:
                        # If no JSON found, return the text as is
                        # Log the partial extraction
                        extraction_details = {
                            "file_type": "pdf",
                            "extraction_type": data_type,
                            "summary": f"Extracted raw text from PDF (no structured data found)"
                        }
                        log_data_extraction(
                            file_handle=file_handle,
                            extraction_type=data_type,
                            extraction_details=extraction_details,
                            tags=["extraction", data_type, "pdf", "raw_text"]
                        )
                        
                        return json.dumps({"raw_text": text}, indent=2)
                except json.JSONDecodeError:
                    # If JSON parsing fails, return the text as is
                    # Log the partial extraction
                    extraction_details = {
                        "file_type": "pdf",
                        "extraction_type": data_type,
                        "summary": f"Extracted raw text from PDF (JSON parsing failed)"
                    }
                    log_data_extraction(
                        file_handle=file_handle,
                        extraction_type=data_type,
                        extraction_details=extraction_details,
                        tags=["extraction", data_type, "pdf", "json_error"]
                    )
                    
                    return json.dumps({"raw_text": result["text"]}, indent=2)
            else:
                error_message = result.get("error", "Unknown error")
                logger.error(f"Error extracting data from PDF: {error_message}")
                
                # Log the failed extraction
                extraction_details = {
                    "file_type": "pdf",
                    "extraction_type": data_type,
                    "error": error_message
                }
                log_data_extraction(
                    file_handle=file_handle,
                    extraction_type=data_type,
                    extraction_details=extraction_details,
                    tags=["extraction_error", data_type, "pdf"]
                )
                
                return json.dumps({"error": error_message})
        else:
            # Log the unsupported file type
            extraction_details = {
                "file_extension": file_extension,
                "error": f"Unsupported file type: {file_extension}"
            }
            log_data_extraction(
                file_handle=file_handle,
                extraction_type=data_type,
                extraction_details=extraction_details,
                tags=["extraction_error", "unsupported_file_type"]
            )
            
            return json.dumps({"error": f"Unsupported file type: {file_extension}"})
            
    except FileNotFoundError:
        logger.error(f"File not found: {file_handle}")
        
        # Log the error
        extraction_details = {
            "error": f"File not found: {file_handle}"
        }
        log_data_extraction(
            file_handle=file_handle,
            extraction_type=data_type,
            extraction_details=extraction_details,
            tags=["extraction_error", "file_not_found"]
        )
        
        return json.dumps({"error": f"File not found: {file_handle}"})
    except Exception as e:
        logger.exception(f"Error extracting structured data from {file_handle}: {e}")
        
        # Log the error
        extraction_details = {
            "error": f"Error extracting structured data: {e}"
        }
        log_data_extraction(
            file_handle=file_handle,
            extraction_type=data_type,
            extraction_details=extraction_details,
            tags=["extraction_error"]
        )
        
        return json.dumps({"error": f"Error extracting structured data: {e}"})

@function_tool
def convert_json_to_excel(json_data: str, output_filename: str) -> str:
    """
    Converts JSON data to Excel format.
    
    Args:
        json_data: JSON string containing the data to convert
        output_filename: Name for the output Excel file
        
    Returns:
        The file handle of the created Excel file
    """
    logger.info(f"Converting JSON data to Excel: {output_filename}")
    
    try:
        # Parse the JSON data
        data = json.loads(json_data)
        
        # Ensure output filename has .xlsx extension
        if not output_filename.lower().endswith('.xlsx'):
            output_filename += '.xlsx'
        
        # Convert to DataFrame and then to Excel
        if isinstance(data, list):
            # If data is a list of objects, convert directly to DataFrame
            df = pd.DataFrame(data)
        elif isinstance(data, dict):
            # If data is a nested dictionary, handle differently
            if any(isinstance(v, dict) for v in data.values()):
                # Flatten nested dictionaries
                flattened_data = {}
                for key, value in data.items():
                    if isinstance(value, dict):
                        for sub_key, sub_value in value.items():
                            flattened_data[f"{key}_{sub_key}"] = sub_value
                    else:
                        flattened_data[key] = value
                df = pd.DataFrame([flattened_data])
            else:
                # Simple dictionary, convert to single row DataFrame
                df = pd.DataFrame([data])
        else:
            return f"Error: Invalid JSON data format"
        
        # Create Excel file in memory
        excel_buffer = io.BytesIO()
        with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Data')
        
        # Get the bytes
        excel_buffer.seek(0)
        file_bytes = excel_buffer.getvalue()
        
        # Upload the file
        file_handle = storage_service.upload_file(output_filename, file_bytes)
        
        logger.info(f"Successfully converted JSON to Excel: {file_handle}")
        return file_handle
        
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON data")
        return f"Error: Invalid JSON data"
    except Exception as e:
        logger.exception(f"Error converting JSON to Excel: {e}")
        return f"Error converting JSON to Excel: {e}"

@function_tool
def extract_invoice_to_excel(file_handle: str, output_filename: str = "") -> str:
    """
    Extracts invoice data from a document and saves it as an Excel file.
    
    Args:
        file_handle: The handle of the invoice file (PDF or image)
        output_filename: Optional name for the output Excel file
        
    Returns:
        The file handle of the created Excel file
    """
    logger.info(f"Extracting invoice data to Excel from: {file_handle}")
    
    try:
        # Generate default output filename if not provided
        if not output_filename:
            base_name = os.path.splitext(os.path.basename(file_handle))[0]
            output_filename = f"{base_name}_invoice.xlsx"
        
        # Extract structured data from the invoice
        json_data = extract_structured_data(file_handle, "invoice")
        
        # Check if extraction was successful
        data = json.loads(json_data)
        if "error" in data:
            return f"Error extracting invoice data: {data['error']}"
        
        # Convert the JSON data to Excel
        excel_file_handle = convert_json_to_excel(json_data, output_filename)
        
        # Log the successful conversion
        operation_details = {
            "source_file": file_handle,
            "output_file": excel_file_handle,
            "operation": "invoice_to_excel",
            "summary": f"Successfully extracted invoice data and converted to Excel"
        }
        log_agent_action(
            agent_name="Data Extraction Agent",
            action_type="invoice_extraction",
            action_details=operation_details,
            outcome=f"Created Excel file: {excel_file_handle}",
            tags=["invoice", "excel", "conversion"]
        )
        
        return excel_file_handle
        
    except Exception as e:
        logger.exception(f"Error extracting invoice to Excel from {file_handle}: {e}")
        
        # Log the error
        operation_details = {
            "source_file": file_handle,
            "operation": "invoice_to_excel",
            "error": str(e)
        }
        log_agent_action(
            agent_name="Data Extraction Agent",
            action_type="invoice_extraction",
            action_details=operation_details,
            outcome=f"Failed to extract invoice data: {e}",
            tags=["invoice", "excel", "conversion", "error"]
        )
        
        return f"Error extracting invoice to Excel: {e}"

@function_tool
def extract_table_from_document(file_handle: str, output_filename: str = "", page_number: int = 1) -> str:
    """
    Extracts table data from a document and saves it as an Excel file.
    
    Args:
        file_handle: The handle of the document file (PDF or image)
        output_filename: Optional name for the output Excel file
        page_number: Page number to extract table from (for PDFs with multiple pages)
        
    Returns:
        The file handle of the created Excel file
    """
    logger.info(f"Extracting table from document: {file_handle}, page: {page_number}")
    
    try:
        # Generate default output filename if not provided
        if not output_filename:
            base_name = os.path.splitext(os.path.basename(file_handle))[0]
            output_filename = f"{base_name}_table.xlsx"
        
        # Extract structured data from the document
        json_data = extract_structured_data(file_handle, "table")
        
        # Check if extraction was successful
        data = json.loads(json_data)
        if "error" in data:
            return f"Error extracting table data: {data['error']}"
        
        # Convert the JSON data to Excel
        excel_file_handle = convert_json_to_excel(json_data, output_filename)
        
        return excel_file_handle
        
    except Exception as e:
        logger.exception(f"Error extracting table from document {file_handle}: {e}")
        return f"Error extracting table from document: {e}"
