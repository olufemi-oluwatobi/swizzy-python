import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class FileStorageService:
    """
    A simple file storage service using the local filesystem.
    Handles are equivalent to filenames within the base directory.
    """

    def __init__(self, base_directory: str = "file_store", public_mount_path: str = "/files"):
        self.base_directory = base_directory
        # Ensure the base directory exists
        os.makedirs(self.base_directory, exist_ok=True)
        # Path prefix used for generating public URLs
        self.public_mount_path = public_mount_path.rstrip('/')
        logger.info(f"Initialized FileStorageService with base directory: {self.base_directory}")

    def _get_full_path(self, file_handle: str) -> str:
        """Constructs the full path for a given file handle."""
        # Basic security check: prevent path traversal
        if ".." in file_handle or file_handle.startswith("/"):
             raise ValueError(f"Invalid file handle contains restricted characters: {file_handle}")
        return os.path.join(self.base_directory, file_handle)

    def upload_file(self, file_identifier: str, file_content: bytes) -> str:
        """
        Saves file content to the storage.

        Args:
            file_identifier: The desired name/identifier for the file (will be used as the handle).
            file_content: The file content as bytes.

        Returns:
            The file handle (which is the file_identifier).

        Raises:
            IOError: If there's an error writing the file.
            ValueError: If file_identifier is invalid.
        """
        full_path = self._get_full_path(file_identifier)
        try:
            with open(full_path, "wb") as f:
                f.write(file_content)
            logger.info(f"Successfully uploaded file: {file_identifier} to {full_path}")
            return file_identifier # Use the identifier as the handle
        except IOError as e:
            logger.error(f"Failed to upload file {file_identifier}: {e}")
            raise
        except ValueError as e:
            logger.error(f"Invalid file identifier provided: {e}")
            raise


    def download_file(self, file_handle: str) -> bytes:
        """
        Downloads file content from storage.

        Args:
            file_handle: The handle (filename) of the file to download.

        Returns:
            The file content as bytes.

        Raises:
            FileNotFoundError: If the file corresponding to the handle does not exist.
            IOError: If there's an error reading the file.
            ValueError: If file_handle is invalid.
        """
        full_path = self._get_full_path(file_handle)
        if not os.path.exists(full_path):
            logger.error(f"File not found for handle: {file_handle} at path: {full_path}")
            raise FileNotFoundError(f"No file found for handle: {file_handle}")
        try:
            with open(full_path, "rb") as f:
                content = f.read()
            logger.info(f"Successfully downloaded file: {file_handle}")
            return content
        except IOError as e:
            logger.error(f"Failed to download file {file_handle}: {e}")
            raise
        except ValueError as e:
             logger.error(f"Invalid file handle provided: {e}")
             raise


    def get_public_url(self, file_handle: str) -> Optional[str]:
        """
        Gets a publicly accessible URL for the file, if applicable.
        Assumes the base_directory is mounted statically.

        Args:
            file_handle: The handle (filename) of the file.

        Returns:
            A URL string (e.g., '/files/my_document.txt') or None if the file doesn't exist
            or the concept isn't applicable.

        Raises:
            ValueError: If file_handle is invalid.
        """
        full_path = self._get_full_path(file_handle) # Raises ValueError if handle is bad
        if os.path.exists(full_path):
            url = f"{self.public_mount_path}/{file_handle}"
            logger.info(f"Generated public URL for {file_handle}: {url}")
            return url
        else:
            logger.warning(f"Cannot generate public URL for non-existent file handle: {file_handle}")
            return None


    def delete_file(self, file_handle: str) -> None:
        """
        Deletes a file from storage.

        Args:
            file_handle: The handle (filename) of the file to delete.

        Raises:
            FileNotFoundError: If the file does not exist.
            IOError: If there's an error deleting the file.
            ValueError: If file_handle is invalid.
        """
        full_path = self._get_full_path(file_handle) # Raises ValueError if handle is bad
        if not os.path.exists(full_path):
             logger.error(f"Attempted to delete non-existent file handle: {file_handle}")
             raise FileNotFoundError(f"No file found for handle: {file_handle}")
        try:
            os.remove(full_path)
            logger.info(f"Successfully deleted file: {file_handle}")
        except IOError as e:
            logger.error(f"Failed to delete file {file_handle}: {e}")
            raise
