import logging
from app.file_storage import FileStorageService

logger = logging.getLogger(__name__)

# Define constants used by the service if needed elsewhere, or keep them local
FILE_STORE_DIRECTORY = "file_store"
PUBLIC_FILES_MOUNT_PATH = "/files"

logger.info("Initializing shared services...")
storage_service = FileStorageService(
    base_directory=FILE_STORE_DIRECTORY,
    public_mount_path=PUBLIC_FILES_MOUNT_PATH
)
logger.info("FileStorageService initialized.")

# You could add other shared services here later (e.g., database connections)
