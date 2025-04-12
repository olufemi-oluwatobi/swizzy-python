import io
import json
import pandas as pd
from typing import Dict, Any
from app.services.storage_service import storage_service

def read_excel_all(file_handle: str) -> Dict[str, pd.DataFrame]:
    """Helper to read all sheets from Excel file"""
    file_bytes = storage_service.download_file(file_handle)
    return pd.read_excel(io.BytesIO(file_bytes), sheet_name=None)

def write_excel_file(sheets_data: Dict[str, pd.DataFrame], filename: str) -> str:
    """Helper to write multiple sheets to Excel file"""
    # Convert DataFrames to list format
    sheets_list = []
    for sheet_name, df in sheets_data.items():
        sheet_data = {
            "name": sheet_name,
            "data": [df.columns.tolist()] + df.values.tolist()
        }
        sheets_list.append(sheet_data)
        
    spreadsheet_data = {"sheets": sheets_list}
    
    # Write to bytes buffer
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        for sheet_name, df in sheets_data.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)
            
    return storage_service.upload_file(filename, output.getvalue())

def get_excel_bytes(file_handle: str) -> bytes:
    """Get raw bytes of an Excel file"""
    return storage_service.download_file(file_handle)
