import logging
from app.file_storage import FileStorageService
from agents import Runner, Tool
from app.tools.memory_tools import *
from app.tools.content_tools import *

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

class MemoryAgent(Tool):
    def __init__(self, agent_config, tools):
        super().__init__()
        self.agent_config = agent_config
        self.tools = tools
        

        # Initialize the tools
        self.available_tools = [
            AddMemory,
            ListMemory,
            DeleteMemory,
            GetMemory,
        ]+tools

    async def __call__(self, input):
        result = await Runner.run(self.agent_config, input=input, tools=self.available_tools)
        return result

