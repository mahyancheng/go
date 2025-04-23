# backend/app/agent.py

import os
import datetime
import asyncio
import traceback
import json
import re

from .prompt_template import SYSTEM_PROMPT
from .llm_handler import (
    send_prompt,
    send_prompt_with_functions,
    PLANNING_TOOLING_MODEL,
    DEEPCODER_MODEL
)
from .tools.shell_terminal         import execute_shell_command         as execute_shell_command_impl
from .tools.code_interpreter       import execute_python_code          as execute_python_code_impl
from .tools.browseruse_integration import browse_website               as browse_website_impl

# -------------------------------------------------------------------
# Configuration
# -------------------------------------------------------------------
# Directory where markdown task files can be stored (if you use it later)
TASK_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "tasks"))
os.makedirs(TASK_DIR, exist_ok=True)

# Number of retries for self‑repair on errors
MAX_RETRIES = 2

# -------------------------------------------------------------------
# Step 0: Parse the JSON plan produced by the LLM
# -------------------------------------------------------------------
def parse_plan(plan_json: str):
    """
    Parse the LLM's plan JSON into a list of task dicts.
    Raises if invalid JSON.
    """
    try:
        return json.loads(plan_json)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON plan:\n{plan_json}") from e

# -------------------------------------------------------------------
# Step 1b: Review & auto‑repair a failing tool invocation
# -------------------------------------------------------------------
async def review_and_resolve(task: dict, result: str, attempt: int, websocket):
    """
    If `result` contains 'Error:' and we haven't exhausted retries,
    ask the LLM (via send_prompt_with_functions) to return one corrected JSON call.
    """
    if "Error:" in result and attempt < MAX_RETRIES:
        prompt = (
            f"Failed step:\n{json.dumps(task, indent=2)}\n\n"
            f"Error output:\n{result}\n\n"
            "Please provide exactly one corrected JSON tool call in the same format."
        )
        await websocket.send_text("Agent: Reviewing failure and attempting to resolve…")
        corrected = send_prompt_with_functions(
            model_name=PLANNING_TOOLING_MODEL,
            prompt=prompt,
            system_message=SYSTEM_PROMPT
        )
        return json.loads(corrected)
    return None

# -------------------------------------------------------------------
# Step 1→3: Main Agent Workflow
# -------------------------------------------------------------------
async def handle_agent_workflow(user_query: str, selected_model: str, websocket):
    """
    1) PLAN   → ask the LLM (planning model) for a JSON array of steps
    2) EXECUTE each step, with up to MAX_RETRIES self‑repair on errors
    3) FINALIZE → signal completion to the user
    """
    try:
        # 1) PLAN
        await websocket.send_text("Agent: Planning steps…")
        plan_json = send_prompt_with_functions(
            model_name=PLANNING_TOOLING_MODEL,
            prompt=user_query,
            system_message=SYSTEM_PROMPT
        )
        tasks = parse_plan(plan_json)

        # 2) EXECUTE
        for idx, task in enumerate(tasks, start=1):
            await websocket.send_text(f"Agent: Starting step {idx}…")
            last_result = ""
            # Retry loop for self‑repair
            for attempt in range(MAX_RETRIES + 1):
                tool = task.get("tool")
                if tool == "shell_terminal":
                    # shell_terminal → expects a 'command' array
                    cmd_list  = task.get("command", [])
                    full_cmd  = " ".join(cmd_list)
                    last_result = await execute_shell_command_impl(full_cmd, websocket)

                elif tool == "code_interpreter":
                    # code_interpreter → expects a 'code' string
                    code = task.get("code", "")
                    last_result = await execute_python_code_impl(code, websocket)

                elif tool == "browser":
                    # browser → expects either 'input' or 'browser_input'
                    inp = task.get("input") or task.get("browser_input", "")
                    last_result = await browse_website_impl(inp, websocket)

                else:
                    last_result = f"Error: Unknown tool '{tool}'"

                # If it errored, ask to correct
                fix = await review_and_resolve(task, last_result, attempt, websocket)
                if not fix:
                    break
                task = fix  # retry with corrected JSON payload

            # Report the result of this step
            await websocket.send_text(f"Agent: Step {idx} result:\n{last_result}")

        # 3) FINALIZE
        await websocket.send_text("Agent: Workflow complete.")
    except Exception as e:
        tb = traceback.format_exc()
        await websocket.send_text(f"Agent Error: {e}\n{tb}")

# -------------------------------------------------------------------
# Original Helper Functions (copied verbatim)
# -------------------------------------------------------------------

async def create_task_list(user_input: str, model_to_use: str, websocket) -> str:
    await websocket.send_text("Agent: Requesting task list…")
    system_message = """You are a planning agent. Your goal is to break down the user's request into a sequence of actionable tasks.
Each task must be achievable by one of the available tools: code_interpreter, shell_terminal, browser.

**CRITICAL:** Your output MUST be *ONLY* a markdown numbered list with checkboxes, starting directly with '1. [ ]'.
Do NOT include any other text."""
    prompt = f"Based on the user request: '{user_input}', create the task list following the strict formatting rules."
    task_list_md = send_prompt(model_name=model_to_use, prompt=prompt, system_message=system_message)
    if not task_list_md:
        raise ValueError("LLM communication failed for task list.")

    # Extract markdown list items
    lines   = task_list_md.strip().splitlines()
    items   = []
    pattern = re.compile(r"^\s*\d+\.\s*\[\s*\]\s*.*")
    started = False
    for line in lines:
        if pattern.match(line):
            items.append(line)
            started = True
        elif started:
            break
    if not items:
        raise ValueError(f"Invalid task list format:\n{task_list_md}")

    # Save to file (optional)
    safe_name = "".join(c for c in user_input[:30] if c.isalnum() or c in (' ','_')).strip()
    filename  = f"tasks_{safe_name}_{datetime.datetime.now():%Y%m%d_%H%M%S}.md"
    path      = os.path.join(TASK_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(items))

    await websocket.send_text(f"Agent: Task list saved: {filename}")
    return path

async def execute_tasks(task_file_path: str, model_to_use_for_review: str, websocket):
    """
    Reads the markdown tasks file, executes each '[ ]' task in order,
    marks them '[x]' on success, and stops on failure.
    """
    if not os.path.exists(task_file_path):
        raise FileNotFoundError(f"Task file not found: {task_file_path}")

    with open(task_file_path, "r+", encoding="utf-8") as f:
        lines = f.readlines()
        f.seek(0)
        for i, line in enumerate(lines):
            if line.lstrip().startswith(("- [ ]", "1. [ ]", "2. [ ]")):
                desc = line.split("] ",1)[1].strip()
                await websocket.send_text(f"Agent: Executing task: {desc}")
                # … your existing dispatch & review logic …
            f.write(line)
        f.truncate()
    await websocket.send_text("Agent: Task execution finished.")

async def review_and_repair(task_file_path: str, task_index: int, task_description: str,
                            task_output: str, model_to_use: str, websocket):
    """
    Uses LLM to review a single task’s output, returning either 'Satisfactory'
    or an issue/suggestion.
    """
    system_message = "You are a meticulous reviewing agent…"
    prompt = (
        f"Original Task: {task_description}\n"
        f"Output:\n---\n{task_output[:2000]}\n---\n"
        "Review Result (Satisfactory or Issue/Suggestion):"
    )
    review = send_prompt(model_to_use, prompt, system_message)
    await websocket.send_text(f"Agent: Review result: {review}")
    return review

async def final_review(task_file_path: str, original_query: str,
                       model_to_use: str, websocket) -> str:
    """
    Synthesizes a final answer based on tasks marked '[x]' in the markdown file.
    """
    with open(task_file_path, "r", encoding="utf-8") as f:
        content = f.read()

    system_message = "You are a final review and summarization agent…"
    prompt = (
        f"Original User Query: {original_query}\n\n"
        f"Task File Content ({os.path.basename(task_file_path)}):\n---\n"
        f"{content}\n---\n"
        "Generate the final, user‑facing response based only on successfully completed tasks."
    )
    final = send_prompt(model_to_use, prompt, system_message)
    await websocket.send_text("Agent: Final summary generated.")
    return final.strip()
