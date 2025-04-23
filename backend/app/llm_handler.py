# backend/app/llm_handler.py

import ollama
import os
from dotenv import load_dotenv
import traceback

# Load environment variables (looking for .env in backend/)
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path=dotenv_path)

# Model names (can be overridden via env)
PLANNING_TOOLING_MODEL      = os.getenv("PLANNING_TOOLING_MODEL",      "llama3:latest")
DEEPCODER_MODEL             = os.getenv("DEEPCODER_MODEL",             "deepcoder:latest")
BROWSER_AGENT_INTERNAL_MODEL= os.getenv("BROWSER_AGENT_INTERNAL_MODEL","qwen2.5:7b")
OLLAMA_BASE_URL             = os.getenv("OLLAMA_ENDPOINT",             "http://localhost:11434/api/chat")

# ======================================================================
#  MODEL LOADING
# ======================================================================
def load_model(model_name: str):
    """Pulls the given Ollama model from the configured host."""
    if not model_name:
        print("Warning: empty model name, skipping load.")
        return None
    try:
        client = ollama.Client(host=OLLAMA_BASE_URL)
        print(f"Ensuring model '{model_name}' is available at {OLLAMA_BASE_URL}...")
        client.pull(model_name)
        print(f"Model '{model_name}' ready.")
        return model_name
    except ollama.ResponseError as e:
        print(f"[Ollama API Error] {model_name} (Status {e.status_code}): {e.error}")
        traceback.print_exc()
        return None
    except Exception as e:
        print(f"[Error] loading model '{model_name}': {e}")
        traceback.print_exc()
        return None

print("\n--- Loading LLM Models ---")
_models = {
    "planning":    load_model(PLANNING_TOOLING_MODEL),
    "deepcoder":   load_model(DEEPCODER_MODEL),
    "browser":     load_model(BROWSER_AGENT_INTERNAL_MODEL),
}
print("--- Model Loading Complete ---")
if not _models["planning"] or not _models["browser"]:
    print(f"FATAL: planning or browser model failed to load. Check Ollama at {OLLAMA_BASE_URL}")

# ======================================================================
#  PROMPT SENDING
# ======================================================================
def send_prompt(model_name: str, prompt: str, system_message: str = None) -> str:
    """
    Send `prompt` to Ollama `model_name`, optionally with a `system_message`.
    Returns the assistant's content, or None on failure.
    """
    # Determine which slot this model occupies
    key = None
    if model_name == PLANNING_TOOLING_MODEL:       key = "planning"
    elif model_name == DEEPCODER_MODEL:            key = "deepcoder"
    elif model_name == BROWSER_AGENT_INTERNAL_MODEL:key = "browser"

    # If a preloaded model, ensure it is ready
    if key and not _models.get(key):
        print(f"[Error] Model '{model_name}' not loaded at startup.")
        return None
    # Otherwise, attempt on‑demand load
    if not key:
        if not load_model(model_name):
            print(f"[Error] Could not load model on demand: {model_name}")
            return None

    messages = []
    if system_message:
        messages.append({"role": "system",  "content": system_message})
    messages.append({"role": "user",    "content": prompt})

    try:
        client   = ollama.Client(host=OLLAMA_BASE_URL)
        print(f"Sending prompt to '{model_name}'…")
        response = client.chat(model=model_name, messages=messages)
        # Ollama returns a dict { "message": { "role":..., "content":... }, … }
        msg = response.get("message") or {}
        content = msg.get("content")
        print(f"Received response from '{model_name}'.")
        return content
    except ollama.ResponseError as e:
        print(f"[Ollama API Error] chat@{model_name} (Status {e.status_code}): {e.error}")
        return None
    except Exception as e:
        print(f"[Error] during Ollama chat '{model_name}': {e}")
        traceback.print_exc()
        return None

def send_prompt_with_functions(model_name: str, prompt: str, system_message: str = None) -> str:
    """
    Alias for send_prompt — provided so agent.py can call it
    when using the JSON‑tool‐calling style.
    """
    return send_prompt(model_name, prompt, system_message)
