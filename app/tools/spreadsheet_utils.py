import io
import json
import pandas as pd
from typing import Dict, Any
from logging import getLogger
from app.services.storage_service import storage_service


logger = getLogger(__name__)
def read_excel_all(file_handle: str) -> Dict[str, pd.DataFrame]:
    """Helper to read all sheets from Excel file"""
    file_bytes = storage_service.download_file(file_handle)
    return pd.read_excel(io.BytesIO(file_bytes), sheet_name=None)

# In app/tools/spreadsheet_utils.py
import pandas as pd
from pandas.io.formats.style import Styler # Crucial import
import io
from typing import Dict, Any

def get_excel_bytes_from_dfs(dfs_or_stylers: Dict[str, Any]) -> bytes:
    """
    Generates Excel file bytes from a dictionary containing DataFrames or Styler objects.

    Args:
        dfs_or_stylers: Dictionary mapping sheet names to pandas DataFrames or Styler objects.

    Returns:
        Bytes representing the generated Excel file.
    """
    excel_bytes_io = io.BytesIO()
    try:
        # Use 'openpyxl' engine for better styling support
        with pd.ExcelWriter(excel_bytes_io, engine='openpyxl') as writer:
            for sheet_name, obj in dfs_or_stylers.items():
                if isinstance(obj, Styler):
                    # Use the Styler's method to write styled data
                    obj.to_excel(writer, sheet_name=sheet_name, index=False) # Adjust index=False/True as needed
                elif isinstance(obj, pd.DataFrame):
                    # Write standard DataFrame
                    obj.to_excel(writer, sheet_name=sheet_name, index=False) # Adjust index=False/True as needed
                else:
                    logger.warning(f"Unsupported type for sheet '{sheet_name}': {type(obj)}. Skipping.")
        logger.info("Successfully wrote all sheets to ExcelWriter buffer.")
        return excel_bytes_io.getvalue()
    except Exception as e:
        logger.exception(f"Error during Excel byte generation: {e}")
        # Depending on desired behavior, re-raise or return empty/error bytes
        raise # Re-raise the exception to be caught by the calling script execution

# Make sure read_excel_all, write_excel_file etc. are also robust


def write_excel_file(excel_bytes: bytes, filename: str) -> str:
    """Helper to write multiple sheets to Excel file"""
    # Convert DataFrames to list format
    return storage_service.upload_file(filename, excel_bytes)


def get_excel_bytes(file_handle: str) -> bytes:
    """Get raw bytes of an Excel file"""
    return storage_service.download_file(file_handle)
