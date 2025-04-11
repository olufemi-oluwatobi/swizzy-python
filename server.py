import os

from logging import getLogger
from typing import List, Annotated
from dotenv import load_dotenv

# Load environment variables first, before any other imports
load_dotenv()

# Now import the rest after environment is set up
from agents import Runner
from fastapi import FastAPI, Request, UploadFile, File as FastApiFile, Form, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# Your application-specific imports
from app.agent_config import starting_agent, memory_agent
from app.services import storage_service, FILE_STORE_DIRECTORY, PUBLIC_FILES_MOUNT_PATH

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
    try:
        for file in files:
            if file.filename:
                safe_filename = os.path.basename(file.filename)
                if not safe_filename:
                    continue

                content = await file.read()
                file_handle = storage_service.upload_file(file_identifier=safe_filename, file_content=content)
                uploaded_file_handles.append(file_handle)
                logger.info(f"Uploaded file '{safe_filename}' with handle: {file_handle}")
            else:
                logger.debug("Skipping file upload due to empty filename.")

        # Prepare input for the agent runner as a single string
        if uploaded_file_handles:
            # Append file handles to the message string
            file_info = "\n\n[Attached Files: " + ", ".join(uploaded_file_handles) + "]"
            agent_run_input = message + file_info
        else:
            # Just use the message if no files were uploaded
            agent_run_input = message

        # Log the actual input being sent to the runner.
        logger.info(f"Running starting agent with input string: '{agent_run_input}'")

        # --- Agent Execution (Handoffs handled internally by agents library) ---
        # Simply run the starting agent. Handoffs will occur automatically if needed.
        result = await Runner.run(starting_agent, input=agent_run_input)
        logger.info(f"Runner returned: {result}")

        # Check result type before accessing attributes
        if result and hasattr(result, 'final_output') and result.final_output is not None:
            response_data = {"response": result.final_output}
            if hasattr(result.final_output, 'file_link') and result.final_output.file_link:
                response_data["file_link"] = result.final_output.file_link
            elif isinstance(result.final_output, dict) and "file_link" in result.final_output:
                response_data["file_link"] = result.final_output["file_link"]
            response_data["response"] = result.final_output.get("description", "Processed file.")
            logger.info(f"Response returned to user: {response_data}")
            return response_data
        else:
          logger.info("Empty response returned to user")
          return {"response": "ok"}
    except Exception as e:
        logger.exception(f"Error processing message or files: {e}")
        raise HTTPException(status_code=500, detail=f"An unexpected server error occurred: {e}")


# --- Main Execution Block ---
if __name__ == "__main__":
    import uvicorn
    print("Starting Uvicorn server...")
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)