# backend/run_browser_task.py
import asyncio
import sys
import os
import json
import traceback
import logging
from dotenv import load_dotenv

# --- Configure Logging for UTF-8 and stderr ---
logging.basicConfig(
    level=logging.INFO, stream=sys.stderr,
    format='%(asctime)s [SUBPROCESS:%(levelname)s] [%(name)s] %(message)s',
    datefmt='%H:%M:%S', encoding='utf-8', force=True
)
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('httpcore').setLevel(logging.WARNING)

# --- Setup sys.path ---
SCRIPT_DIR = os.path.dirname(__file__)
# No longer need to add app to path, importing directly

# --- Imports for BrowserUse and LLM ---
try:
    from browser_use.agent.service import Agent as BrowserUseAgent
    from browser_use.browser.browser import Browser, BrowserConfig
    from browser_use.browser.context import BrowserContext, BrowserContextConfig, BrowserContextWindowSize
    from langchain_ollama import ChatOllama
    # Import Gemini if using it
    # from langchain_google_genai import ChatGoogleGenerativeAI
    logging.info("Subprocess: Dependencies imported successfully.")
except ImportError as e:
    logging.exception(f"FATAL: Subprocess Import Error: {e}")
    print(json.dumps({"error": f"Subprocess failed library import: {e}"})); sys.exit(1)
except Exception as e:
     logging.exception(f"FATAL: Unexpected error during subprocess import: {e}")
     print(json.dumps({"error": "Subprocess unexpected error importing."})); sys.exit(1)

# --- Configuration ---
load_dotenv(dotenv_path=os.path.join(SCRIPT_DIR, '.env')) # Load .env from backend/
BROWSER_AGENT_INTERNAL_MODEL = os.getenv("BROWSER_AGENT_INTERNAL_MODEL", "qwen2.5:7b") # Defaulting to Qwen 7B
OLLAMA_BASE_URL = os.getenv("OLLAMA_ENDPOINT", "http://localhost:11434")
# GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY") # Uncomment if using Gemini

# --- Set asyncio policy ---
if sys.platform == "win32":
    logging.info(f"--- Browser Subprocess: Using default asyncio policy: {type(asyncio.get_event_loop_policy()).__name__} ---")
    pass # Use default ProactorEventLoop

# --- Main Task Execution Logic ---
async def run_task(instructions: str):
    """Initializes resources, creates agent, runs task, cleans up."""
    llm_instance = None; browser_instance = None; context_instance = None
    result_text = "Task started but no result captured."
    try:
        # 1. Initialize LLM
        logging.info(f"Initializing LLM ({BROWSER_AGENT_INTERNAL_MODEL})...")
        try:
            # --- CHOOSE LLM PROVIDER ---
            # Option 1: Ollama (Current default)
            llm_instance = ChatOllama(model=BROWSER_AGENT_INTERNAL_MODEL, base_url=OLLAMA_BASE_URL, temperature=0.0)
            # Option 2: Google Gemini (Uncomment below, comment out Ollama, set GOOGLE_API_KEY in .env)
            # if not GOOGLE_API_KEY: raise ValueError("GOOGLE_API_KEY not found in environment.")
            # llm_instance = ChatGoogleGenerativeAI(model="gemini-1.5-flash-latest", google_api_key=GOOGLE_API_KEY, temperature=0.0, convert_system_message_to_human=True)
            # --------------------------
            logging.info("LLM initialized.")
        except Exception as e: raise RuntimeError(f"Failed to initialize LLM: {e}") from e

        # 2. Initialize Browser
        logging.info("Initializing Browser (headless=False)...")
        try:
             browser_config = BrowserConfig(headless=False, disable_security=True)
             browser_instance = Browser(config=browser_config)
             logging.info("Browser initialized.")
        except Exception as e: raise RuntimeError(f"Failed to initialize Browser: {e}") from e

        # 3. Initialize Context
        logging.info("Creating Browser Context...")
        try:
             context_config = BrowserContextConfig(browser_window_size=BrowserContextWindowSize(width=1280, height=1080))
             context_instance = await browser_instance.new_context(config=context_config)
             logging.info("Context created.")
        except Exception as e: raise RuntimeError(f"Failed to create Context: {e}") from e

        # 4. Initialize Agent
        logging.info("Initializing BrowserUseAgent...")
        try:
             agent_instance = BrowserUseAgent(task=instructions, browser=browser_instance, browser_context=context_instance, llm=llm_instance, use_vision=False)
             logging.info("BrowserUseAgent initialized.")
        except Exception as e: raise RuntimeError(f"Failed to initialize Agent: {e}") from e

        # 5. Run Agent Task
        logging.info("Running agent task...")
        result_history = await asyncio.wait_for(agent_instance.run(), timeout=180.0)
        logging.info("Agent run completed.")

        # 6. Extract Result
        if result_history and hasattr(result_history, 'final_result'): result_text = result_history.final_result() or "Action finished, no result text."
        elif result_history is not None: result_text = str(result_history)
        return {"result": result_text}

    except asyncio.TimeoutError: logging.error("Browser action timed out."); return {"error": "Browser action timed out in subprocess."}
    except Exception as e: logging.exception(f"Error during run_task: {e}"); return {"error": f"Error in subprocess run_task: {e}"}
    finally: # 7. Cleanup
        logging.info("Cleaning up browser resources...");
        if context_instance and hasattr(context_instance, 'is_closed') and not context_instance.is_closed:
            try: await context_instance.close(); logging.info("Context closed.")
            except Exception as e_ctx: logging.warning(f"Cleanup context error: {e_ctx}")
        if browser_instance:
            try: await browser_instance.close(); logging.info("Browser closed.")
            except Exception as e_brw: logging.warning(f"Cleanup browser error: {e_brw}")
        logging.info("Cleanup finished.")

# --- Script Entry Point ---
if __name__ == "__main__":
    load_dotenv(dotenv_path=os.path.join(SCRIPT_DIR, '.env'))
    if len(sys.argv) < 2: print(json.dumps({"error": "No input JSON provided."})); sys.exit(1)
    input_json_str = sys.argv[1]; result_data = {"error": "Subprocess main block failed."}
    try:
        input_data = json.loads(input_json_str); instructions = input_data.get("instructions")
        if not instructions: result_data = {"error": "Missing 'instructions' key."}
        else: result_data = asyncio.run(run_task(instructions))
    except json.JSONDecodeError: result_data = {"error": "Invalid JSON input."}
    except Exception as main_err: logging.exception(f"FATAL: Unexpected error: {main_err}"); result_data = {"error": f"Fatal error: {main_err}"}
    finally: # Print final JSON result/error to STDOUT
        try: print(json.dumps(result_data))
        except Exception as print_err: print(json.dumps({"error": f"Failed to serialize result: {print_err}"}))
        sys.exit(0 if "result" in result_data else 1)