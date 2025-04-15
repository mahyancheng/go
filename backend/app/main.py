# backend/main.py (FastAPI Version)
import sys
import asyncio
import os # Import os for path joining
from pathlib import Path # Import Path for robust path handling

# --- asyncio Policy Handling ---
# Using default ProactorEventLoop based on Playwright docs for Windows
print(f"--- FastAPI running with Python: {sys.executable} ---")
print(f"--- Using default asyncio policy: {type(asyncio.get_event_loop_policy()).__name__} ---")

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.routing import APIRouter
from fastapi.staticfiles import StaticFiles # Import for static files
import json
import traceback

# --- Import Agent Logic ---
# Assumes this file is in 'backend/' and agent.py is in 'backend/app/'
try:
    from app.agent import handle_agent_workflow
    # Import cleanup functions if using lifespan management (Optional)
    # from app.tools.browseruse_integration import close_browser_context, close_browser_instance
    print("Agent components imported successfully (from app.).")
    AGENT_AVAILABLE = True
except ImportError as e:
    print(f"ERROR: Failed to import agent components from 'app.' : {e}")
    print("Ensure agent.py and tools/ exist within an 'app' subdirectory relative to main.py")
    print("Also check for errors *within* agent.py during its own imports (like SyntaxErrors).")
    traceback.print_exc()
    AGENT_AVAILABLE = False
except Exception as e:
    print(f"ERROR: Unexpected error during 'app.' import: {e}")
    traceback.print_exc()
    AGENT_AVAILABLE = False

# Initialize FastAPI app
app = FastAPI()

api_router = APIRouter()

@api_router.get("/api/health") # Added a simple health check endpoint
async def health_check():
    return {"status": "ok", "agent_available": AGENT_AVAILABLE}

# Include the API router
app.include_router(api_router, prefix="/api") # Prefix API routes

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """ Handles WebSocket connections for FastAPI """
    await websocket.accept()
    print(f"Client connected: {websocket.client}")
    selected_model = "qwen2.5:32b-instruct" # Default for review steps

    if not AGENT_AVAILABLE:
        await websocket.send_text("Agent Error: Backend agent components failed to load.")
        await websocket.close(code=1011); return

    try:
        while True:
            data = await websocket.receive_text()
            try:
                message_data = json.loads(data)
                user_query = message_data.get("query")
                newly_selected_model = message_data.get("model", selected_model)
                if newly_selected_model != selected_model:
                     selected_model = newly_selected_model; print(f"Client {websocket.client} set model to: {selected_model}")
                if user_query:
                    print(f"Received query: '{user_query}' (Review Model: {selected_model}) from {websocket.client}")
                    await handle_agent_workflow(user_query, selected_model, websocket)
                else: await websocket.send_text("Agent Error: Received empty query.")
            except json.JSONDecodeError: await websocket.send_text("Agent Error: Invalid message format."); print(f"Invalid data from {websocket.client}: {data}")
            except WebSocketDisconnect: print(f"Client disconnected during processing: {websocket.client}"); break
            except Exception as e:
                 error_msg = f"Agent Error: Processing error: {e}"
                 print(f"Error processing for {websocket.client}: {e}")
                 traceback.print_exc()
                 try: await websocket.send_text(error_msg)
                 except Exception as send_err: print(f"Could not send error to client {websocket.client}: {send_err}"); pass
    except WebSocketDisconnect:
        print(f"Client disconnected: {websocket.client}")
    except Exception as e:
        print(f"WebSocket Error for {websocket.client}: {e}"); traceback.print_exc()
    finally:
        print(f"Closing connection for {websocket.client}")
        try: await websocket.close(code=1000)
        except Exception: pass

# --- Serve Frontend Static Files ---
# Determine the absolute path to the frontend directory relative to this main.py file
# Assumes main.py is in backend/app/ and frontend is sibling to backend/
script_dir = Path(__file__).parent # Should be backend/app/
backend_dir = script_dir.parent # Should be backend/
root_dir = backend_dir.parent # Should be mahyancheng-go/
frontend_dir = root_dir / "frontend"

if frontend_dir.is_dir():
    print(f"Attempting to serve static files from: {frontend_dir}")
    try:
        app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="static")
        print("Frontend static files mounted successfully.")
    except Exception as e:
         print(f"Error mounting static files: {e}")
         # Fallback route if mounting fails
         @app.get("/")
         async def read_root_fallback():
              return {"message": "Backend running, but couldn't mount frontend static files."}

else:
    print(f"Frontend directory not found at expected path: {frontend_dir}")
    @app.get("/")
    async def read_root_no_frontend():
         return {"message": "Backend running. Frontend directory not found."}


# To run: navigate to 'backend' directory in terminal, activate venv, run:
# uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
