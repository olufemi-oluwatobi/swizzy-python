import os
import uuid
from dataclasses import dataclass, field
from logging import getLogger
from typing import List, Annotated
from dotenv import load_dotenv

from fastapi import FastAPI, Request, UploadFile, File as FastApiFile, Form, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates 
from agents import Runner, RunContextWrapper, function_tool # Added RunContextWrapper, function_tool
from app.context import TaskContext

# Load environment variables first, before any other imports
load_dotenv()

# Your application-specific imports
from app.agent_config import starting_agent, memory_agent
# Removed RunContextWrapper import from here as it's now imported from agents
from app.services.storage_service import storage_service, FILE_STORE_DIRECTORY, PUBLIC_FILES_MOUNT_PATH

# --- Constants ---
STATIC_DIRECTORY = "static"
TEMPLATE_DIRECTORY = "app/templates"


# Store agent state for the session
agent_state = None

# --- Environment Variable Loading ---
# When .env file is present, it will override the environment variables
# Adjust the path if your .env file is elsewhere relative to where you run the script.
# If server.py is inside a 'server' folder and .env is outside it, '../.env' is correct.
# If .env is in the *same* folder as server.py, use '.env' or just load_dotenv().
dotenv_path = "../.env"
print(f"Attempting to load .env file from: {dotenv_path}")

# --- FastAPI App Initialization ---
app = FastAPI()
logger = getLogger(__name__)

# Setup static files and templates
app.mount("/static", StaticFiles(directory=STATIC_DIRECTORY), name="static")
app.mount(PUBLIC_FILES_MOUNT_PATH, StaticFiles(directory=FILE_STORE_DIRECTORY), name="public_files")
templates = Jinja2Templates(directory=TEMPLATE_DIRECTORY)

# --- CORS Middleware ---
# Your CORS configuration allows everything, which is fine for development
# but consider restricting origins in production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Landing Page Route ---
@app.get("/", response_class=HTMLResponse)
async def get_landing_page(request: Request):
    """Serves the index.html template."""
    return templates.TemplateResponse("index.html", {"request": request})


# --- Process Task Endpoint (Handles Swizzy Agent Interaction) ---
@app.post("/process_task")
async def process_task(
    request: Request,
    task: Annotated[str, Form()],
    files: List[UploadFile] = FastApiFile(None),
):
    """
    Handles a task request, processes files, interacts with the Swizzy agent,
    and returns the agent's response.
    """
    logger.info(f"Received task: {task}")
    uploaded_file_handles = []
    task_context = None # Initialize to None

    try:
        # --- Initialize Task Context with a Unique Task ID ---
        task_id = str(uuid.uuid4())  # Generate a unique Task ID
        task_context = TaskContext(task_id=task_id)
        logger.info(f"Initialized TaskContext with ID: {task_id}")

        # --- File Handling ---
        if files:
            for file in files:
                if file.filename:
                    safe_filename = os.path.basename(file.filename)
                    content = await file.read()
                    # File handle generation now happens within the agent tools using task_id
                    # We still need to upload the *original* file for the agent to access
                    # Let's use a temporary naming convention here or pass content directly if possible
                    # For now, we upload with original name, agent tools will reference this
                    # or create new files with task_id prefix.
                    temp_file_handle = storage_service.upload_file(
                        file_identifier=safe_filename, file_content=content
                    )
                    uploaded_file_handles.append(temp_file_handle) # Pass original handle
                    logger.info(
                        f"Uploaded temporary file '{safe_filename}' with handle: {temp_file_handle}"
                    )


        # --- Prepare Agent Input ---
        if uploaded_file_handles:
            # Pass the *original* file handles to the agent
            file_info = "[Attached Files: " + ", ".join(uploaded_file_handles) + "]"
            agent_input = task + file_info
        else:
            agent_input = task
        logger.info(f"Agent input: {agent_input}")


        print(f"Running starting agent with input string: '{agent_input}' and Task ID: {task_id}")


        # --- Agent Interaction (Pass the context) ---
        result = await Runner.run(starting_agent, input=agent_input, context=task_context)

        # --- Log final context state ---
        logger.info(f"[Task {task_id}] Final action log: {task_context.action_log}")

        print(task_context.action_log)

        # --- Response Handling ---
        if result and hasattr(result, "final_output") and result.final_output:
            response_data = {}
            final_output = result.final_output
            # Handle potential file link in the output
            if hasattr(final_output, 'file_link') and final_output.file_link:
                response_data["file_link"] = final_output.file_link
            elif isinstance(final_output, dict) and "file_link" in final_output:
                response_data["file_link"] = final_output["file_link"]
            
            # Set the main response text
            if isinstance(final_output, dict):
                 response_data["response"] = final_output.get("description", str(final_output))
            else:
                 response_data["response"] = str(final_output) # Convert to string if not dict

            logger.info(f"Agent response: {response_data}")
            return response_data
        else:
            logger.info("Agent returned an empty response.")
            return {"response": "ok"}

    except Exception as e:
        # Include task_id in error logging if available
        task_id_str = f"Task {task_context.task_id}: " if task_context else ""
        logger.exception(f"{task_id_str}Error processing task or files: {e}")
        raise HTTPException(status_code=500, detail=f"An unexpected server error occurred: {e}")



# --- Message Endpoint (Modified for File Uploads & FileStorageService) ---
@app.post("/chat")
async def chat(
    request: Request,
    files: List[UploadFile] = FastApiFile(None),
    message: Annotated[str, Form()] = ""
):
    """Handle incoming messages and optional file uploads, using FileStorageService.

    Receives a form with a message and files.
    """
    form_data = await request.form()
    message = form_data.get("message", "")
    uploaded_file_handles = []
    task_context = None # Initialize to None

    try:
        # --- Initialize Task Context with a Unique Task ID ---
        task_id = str(uuid.uuid4())  # Generate a unique Task ID
        task_context = TaskContext(task_id=task_id)
        logger.info(f"Initialized TaskContext with ID: {task_id}")


        for file in files:
            if file.filename:
                safe_filename = os.path.basename(file.filename)
                if not safe_filename:
                    continue

                content = await file.read()
                # Upload original file, agent tools will create task-specific versions if needed
                temp_file_handle = storage_service.upload_file(file_identifier=safe_filename, file_content=content)
                uploaded_file_handles.append(temp_file_handle) # Pass original handle
                logger.info(f"Uploaded temporary file '{safe_filename}' with handle: {temp_file_handle}")
            else:
                logger.debug("Skipping file upload due to empty filename.")

        # Prepare input for the agent runner as a single string
        if uploaded_file_handles:
            # Append *original* file handles to the message strings
            file_info = "[Attached Files: " + ", ".join(uploaded_file_handles) + "]"
            agent_run_input = message + file_info
        else:
            # Just use the message if no files were uploaded
            agent_run_input = message

        # Log the actual input being sent to the runner.
        logger.info(f"Running starting agent with input string: '{agent_run_input}' and Task ID: {task_id}")


        # --- Agent Execution (Pass the context) ---
        result = await Runner.run(starting_agent, input=agent_run_input, context=task_context, max_turns=25)

        # --- Log final context state ---
        logger.info(f"[Task {task_id}] Final action log: {task_context.action_log}")

        logger.info(f"Runner returned: {result}")

        # Check result type before acce ssing attributes
        if result and hasattr(result, 'final_output') and result.final_output is not None:
            response_data = {}
            final_output = result.final_output

            # Handle potential file link in the output
            if hasattr(final_output, 'file_link') and final_output.file_link:
                response_data["file_link"] = final_output.file_link
            elif isinstance(final_output, dict) and "file_link" in final_output:
                response_data["file_link"] = final_output["file_link"]

            # Set the main response text
            if isinstance(final_output, dict):
                 response_data["response"] = final_output.get("description", str(final_output))
            else:
                 response_data["response"] = str(final_output) # Convert to string if not dict

            logger.info(f"Response returned to user: {response_data}")
            return response_data
        else:
          logger.info("Empty response returned to user")
          return {"response": "ok"}
    except Exception as e:
        # Include task_id in error logging if available
        task_id_str = f"Task {task_context.task_id}: " if task_context else ""
        logger.exception(f"{task_id_str}Error processing message or files: {e}")
        raise HTTPException(status_code=500, detail=f"An unexpected server error occurred: {e}")


# --- Memory State Endpoint ---
@app.get("/memory_state")
async def get_memory_state():
    return "Direct memory state access not available."


# --- Main Execution Block ---
if __name__ == "__main__":
    import uvicorn
    print("Starting Uvicorn server...")
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
