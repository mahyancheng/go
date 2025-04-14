# backend/app/llm_handler.py
import ollama
import os
from dotenv import load_dotenv
import traceback

load_dotenv()

# Use Llama 3 for Planning/Tool Selection/Review
PLANNING_TOOLING_MODEL = "llama3:latest" # Or your specific tag e.g., "llama3:8b"
DEEPCODER_MODEL = "deepcoder:latest" # Or just "deepcoder"
# Use Qwen 7B for the browser agent's internal use (used by run_browser_task.py)
BROWSER_AGENT_INTERNAL_MODEL = "qwen2.5:7b"


# --- Model Loading ---
def load_model(model_name: str):
    """Ensures a model is available locally via Ollama."""
    if not model_name: print("Warning: Empty model name skipped."); return None
    try:
        print(f"Ensuring model '{model_name}' is available locally...")
        ollama.pull(model_name); print(f"Model '{model_name}' is ready.")
        return model_name
    except Exception as e: print(f"Error loading '{model_name}': {e}"); traceback.print_exc(); return None

print("\n--- Loading LLM Models ---")
models_loaded = {
    "planning": load_model(PLANNING_TOOLING_MODEL),
    "deepcoder": load_model(DEEPCODER_MODEL),
    "browser_agent": load_model(BROWSER_AGENT_INTERNAL_MODEL)
}
print("--- Model Loading Complete ---")
if not models_loaded["planning"] or not models_loaded["browser_agent"]:
     print("\nFATAL: Essential planning or browser agent LLM failed load.")
     print(f"Ensure Ollama running & models '{PLANNING_TOOLING_MODEL}', '{BROWSER_AGENT_INTERNAL_MODEL}' pulled.")

# --- Prompt Sending ---
def send_prompt(model_name: str, prompt: str, system_message: str = None):
    """Sends a prompt to the specified Ollama model and returns the response content."""
    model_key = None
    if model_name == PLANNING_TOOLING_MODEL: model_key = "planning"
    elif model_name == DEEPCODER_MODEL: model_key = "deepcoder"
    elif model_name == BROWSER_AGENT_INTERNAL_MODEL: model_key = "browser_agent"

    # Check if the specific model needed was loaded successfully
    if model_key and not models_loaded.get(model_key): # Use .get() for safety
        print(f"Error: Model '{model_name}' (key: {model_key}) was not loaded successfully at startup.")
        return None
    elif not model_key: # If not a preloaded model, try loading now
        if not load_model(model_name):
             print(f"Error: Model '{model_name}' could not be loaded.")
             return None

    messages = []
    if system_message: messages.append({'role': 'system', 'content': system_message})
    messages.append({'role': 'user', 'content': prompt})
    try:
        print(f"Sending prompt to model '{model_name}'..."); response = ollama.chat(model=model_name, messages=messages)
        print(f"Raw response from '{model_name}': {str(response)[:500]}...")
        if response and 'message' in response and 'content' in response['message']:
             content = response['message']['content']; print(f"Received content from '{model_name}'."); return content
        else: print(f"Unexpected response structure: {response}"); return None
    except ollama.OllamaAPIError as e: print(f"Error Ollama API '{model_name}': {e}"); return None
    except Exception as e: print(f"Unexpected error Ollama chat '{model_name}': {e}"); traceback.print_exc(); return None