# backend/app/agent.py

import os
import asyncio
import traceback
import json
import re
import time
import shlex
from fastapi import WebSocket # Import WebSocket for type hinting

# Attempt import json_repair
try: from json_repair import repair_json
except ImportError: print("Warning: 'json-repair' not found."); repair_json = lambda s: s

from .prompt_template import SYSTEM_PROMPT
from .llm_handler import simple_prompt # Using the simplified LLM handler interface
# Import tool functions
from .tools.shell_terminal import execute_shell_command as execute_shell_command_impl
from .tools.code_interpreter import execute_python_code as execute_python_code_impl
from .tools.browseruse_integration import browse_website as browse_website_impl

# --- Configuration ---
MAX_RETRIES = 2
MAX_WORKFLOW_STEPS = 10
BROWSER_STEP_LIMIT_SUGGESTION = 15

# --- Helper: Send Task List Update ---
async def send_task_update(websocket: WebSocket, tasks_with_status: list):
    """Formats tasks and sends via WebSocket using TASK_LIST_UPDATE prefix."""
    try:
        tasks_for_ui = [{"description": t.get("description", "Task"), "status": t.get("status", "pending")} for t in tasks_with_status]
        payload = json.dumps(tasks_for_ui)
        await websocket.send_text(f"TASK_LIST_UPDATE:{payload}")
    except Exception as e: print(f"Error sending task update: {e}")

# --- Helper: Parse Tool Output ---
def parse_tool_output(output_str: str) -> dict:
    """Parses the combined string output from tools into structured data."""
    result = {'raw': output_str, 'exit_code': None, 'output': '', 'error': ''}
    if not isinstance(output_str, str): result['error'] = f"Invalid tool output type: {type(output_str)}"; return result
    exit_match = re.search(r'^Exit Code:\s*(-?\d+)', output_str, re.M); result['exit_code'] = int(exit_match.group(1)) if exit_match else None
    out_lines, err_lines, section = [], [], None
    out_mkr, err_mkr = re.compile(r'^(Output|Stdout Log):', re.I), re.compile(r'^(Error|Errors|Stderr Log):', re.I)
    for line in output_str.splitlines():
        if out_mkr.match(line): section = 'out'; continue
        elif err_mkr.match(line): section = 'err'; continue
        elif line.startswith("Exit Code:"): section = None; continue
        if section == 'out': out_lines.append(line)
        elif section == 'err': err_lines.append(line)
    result['output'] = "\n".join(out_lines).strip(); result['error'] = "\n".join(err_lines).strip()
    if not result['output'] and not result['error']:
        clean = output_str.replace(exit_match.group(0), '', 1).strip() if exit_match else output_str
        if result['exit_code'] != 0: result['error'] = clean
        else: result['output'] = clean
    return result

# --- Step 0: Parse Plan ---
def parse_plan(plan_json: str):
    """Parse and validate the LLM's JSON plan, attempting repair."""
    original = plan_json
    try:
        clean = re.sub(r'^```json\s*|\s*```$', '', plan_json, flags=re.M | re.S).strip()
        if not clean: raise ValueError("Empty plan.")
        parsed = json.loads(repair_json(clean))
        if not isinstance(parsed, list):
            if isinstance(parsed, dict) and 'tool' in parsed: parsed = [parsed]
            else: raise ValueError(f"Plan not list: {type(parsed)}")
        valid = []
        for i, task in enumerate(parsed):
            if not isinstance(task, dict): raise ValueError(f"Item {i} not dict: {task}")
            if 'tool' not in task: raise ValueError(f"Task {i} missing 'tool': {task}")
            if not task.get('description'):
                tool, p = task.get('tool','?'), task.get('command') or task.get('code') or task.get('input','')
                task['description'] = f"Run {tool}" + (f" ({str(p)[:50]}...)" if p else f" step {i+1}")
            valid.append(task)
        return valid
    except Exception as e: raise ValueError(f"Plan parse fail: {e}\nOrig:\n{original}") from e

# --- Step 1b: Review & Resolve ---
async def review_and_resolve(task: dict, result_str: str, attempt: int, planner_model_name: str, websocket: WebSocket):
    """Attempt self-correction for a failed step using the specified planner LLM."""
    parsed = parse_tool_output(result_str)
    exit_code, error_content, raw = parsed.get('exit_code'), parsed.get('error'), parsed.get('raw', '')
    is_error, reason = False, "Unknown failure"
    if exit_code is not None and exit_code != 0: is_error, reason = True, f"Non-zero exit ({exit_code})"
    elif any(e in raw.lower() for e in ["error:", "fail", "except", "trace", "timeout", "denied", "not found"]): is_error, reason = True, "Error keyword detected"
    elif exit_code == 0 and not error_content and not parsed.get('output'): is_error, reason = True, "Exit 0 but no output"

    if is_error and attempt < MAX_RETRIES:
        fail_json = json.dumps({k: v for k, v in task.items() if k != 's'}, indent=2)
        prompt = (f"Failed step {attempt+1}/{MAX_RETRIES}:\nTask: {task.get('d','N/A')}\nCall:\n```json\n{fail_json}\n```\nReason: {reason}\nOutput:\n```\n{raw}\n```\n\nProvide ONLY corrected JSON tool call.")
        await websocket.send_text(f"Agent: Reviewing failure ({reason}. Try {attempt + 1})...")
        correction = simple_prompt(model=planner_model_name, prompt=prompt, system=SYSTEM_PROMPT)
        if not correction: await websocket.send_text("Warn: LLM gave no correction."); return None
        try:
            clean = re.sub(r'^```json\s*|\s*```$','',correction, flags=re.M|re.S).strip()
            if not clean: raise ValueError("Empty correction.")
            fixed = json.loads(repair_json(clean))
            if not isinstance(fixed, dict) or 'tool' not in fixed: raise ValueError("Correction invalid.")
            if not fixed.get('description'): fixed['description'] = task.get('d', "Corrected task")
            await websocket.send_text("Agent: Received potential correction."); return fixed
        except Exception as e: await websocket.send_text(f"Error parsing correction: {e}\nRaw: {correction}"); return None
    elif is_error: await websocket.send_text(f"Agent: Step failed, max retries ({MAX_RETRIES}) reached.")
    return None

# --- Step 1→3: Main Agent Workflow ---
async def handle_agent_workflow(user_query: str, planner_model_name: str, websocket: WebSocket):
    """Main execution loop: Plan -> Send Tasks -> Execute Steps -> Final Validation/Summarization -> Finish."""
    tasks = []; stopped = False; failed = False; final_answer = None
    try:
        # 1) PLAN
        await websocket.send_text("Agent: Planning steps...")
        print(f"Using Planner: {planner_model_name}")
        prompt = (
            f"Req: '{user_query}'\n"
            "Plan as JSON list [{\"tool\": t, \"description\": d, params...}]. Tools: shell_terminal, code_interpreter, browser.\n"
            "CRITICAL: Escape Python code for JSON ('\\n', '\\\\', '\\\"').\n"
            "Code context: Previous step result in string var `previous_step_result`.\n"
            f"Aim for ~{MAX_WORKFLOW_STEPS} steps. Final step must present result. Output ONLY JSON list."
        )
        plan_json = simple_prompt(model=planner_model_name, prompt=prompt, system=SYSTEM_PROMPT)
        if not plan_json: raise ValueError("LLM plan empty.")
        raw = parse_plan(plan_json) # Raises ValueError on failure
        tasks = [{'description': t.get('description'), 'status': 'pending', 'original_task': t, 'result': None, 'final_executed_task': None} for t in raw]

        # 2) SEND Initial List
        await send_task_update(websocket, tasks)
        if not tasks: await websocket.send_text("Agent: No steps planned."); return
        await websocket.send_text(f"Agent: Plan: {len(tasks)} steps.")

        # 3) EXECUTE STEPS
        last_successful_output = "No output from previous steps." # Store PARSED output
        count = 0
        for idx, task in enumerate(tasks):
            if count >= MAX_WORKFLOW_STEPS: # Check Limit
                await websocket.send_text(f"**Warn: Max steps ({MAX_WORKFLOW_STEPS}) reached.**")
                stopped = True; break
            tasks[idx]['status'] = 'running'; await send_task_update(websocket, tasks) # Update UI
            await websocket.send_text(f"**Agent: Step {idx+1}/{len(tasks)}: {task['description']}**")
            current, step_res_str, final_task = task['original_task'].copy(), "Error: Step skip.", task['original_task'].copy()

            # Retry Loop
            for attempt in range(MAX_RETRIES + 1):
                tool, params = current.get("tool"), {k:v for k,v in current.items() if k not in ['description','tool','s']}
                await websocket.send_text(f"Tool Input ({tool}): {json.dumps(params, indent=2, ensure_ascii=False)}")
                print(f"Exec Step {idx+1}, Try {attempt+1}: {tool}, Task='{task['description']}'")
                attempt_res_str = ""
                try: # Tool Execution
                    if tool == "shell_terminal":
                        cmd = current.get("command", []); cmd_str=" ".join(shlex.split(" ".join(cmd)) if isinstance(cmd,list) else shlex.split(cmd))
                        attempt_res_str = await execute_shell_command_impl(cmd_str, websocket)
                    elif tool == "code_interpreter":
                        code = current.get("code", "");
                        if not code: raise ValueError("Missing 'code'")
                        safe_prev = last_successful_output.replace('"""', '\\"\\"\\"'); code_prefix = f'previous_step_result = """{safe_prev}"""\n\n'
                        print(f"[Inject] Previous result len {len(last_successful_output)}.")
                        attempt_res_str = await execute_python_code_impl(code_prefix + code, websocket)
                    elif tool == "browser":
                        inp = current.get("input") or current.get("browser_input", ""); browser_model = os.getenv("BROWSER_AGENT_INTERNAL_MODEL", "qwen2.5:7b")
                        if not inp: raise ValueError("Missing 'input'")
                        attempt_res_str = await browse_website_impl(inp, websocket, browser_model=browser_model, context_hint=last_successful_output, step_limit_suggestion=BROWSER_STEP_LIMIT_SUGGESTION)
                    else: attempt_res_str = f"Error: Unknown tool '{tool}'."; break
                    # Check Result
                    step_res_str = attempt_res_str; parsed = parse_tool_output(step_res_str); exit_code = parsed.get('exit_code');
                    step_failed = False
                    if exit_code is not None and exit_code != 0: step_failed = True
                    elif any(e in step_res_str.lower() for e in ["error:", "fail", "except", "timeout"]): step_failed = True
                    await websocket.send_text(f"Tool Output (Try {attempt+1}):\n```\n{step_res_str}\n```"); print(f"Step {idx+1}, Try {attempt+1} Exit={exit_code}, Failed={step_failed}")
                    if not step_failed: final_task = current; break # Success
                    # Error, try correction
                    await websocket.send_text(f"Agent: Step {idx + 1} error (Try {attempt + 1}).")
                    correction = await review_and_resolve(current, step_res_str, attempt, planner_model_name, websocket)
                    if correction:
                        await websocket.send_text(f"Agent: Applying correction (Try {attempt + 2})...")
                        if correction.get('description') != tasks[idx]['description']: tasks[idx]['description'] = correction['description']; await send_task_update(websocket, tasks)
                        current = correction; final_task = current
                    else: break # No correction / Max retries
                except Exception as tool_err: step_res_str=f"Error: Tool exception: {tool_err}\n{traceback.format_exc()}"; await websocket.send_text(f"Error: Tool '{tool}' failed: {tool_err}"); break
            # After Retry Loop
            count += 1
            final_parsed = parse_tool_output(step_res_str); final_exit = final_parsed.get('exit_code')
            final_failed = False
            if final_exit is not None and final_exit != 0: final_failed = True
            elif any(e in step_res_str.lower() for e in ["error:", "fail", "except", "timeout"]): final_failed = True
            final_status = 'error' if final_failed else 'done'
            tasks[idx].update({'status': final_status, 'final_executed_task': final_task, 'result': step_res_str})
            await send_task_update(websocket, tasks); await websocket.send_text(f"**Agent: Step {idx+1} finished: {final_status.upper()}**")
            if final_status == 'error': failed = True; stopped = True; msg = f"Agent Error: Failed step {idx+1}."; await websocket.send_text(f"**{msg}**"); break # Stop workflow
            last_successful_output = final_parsed.get('output') or final_parsed.get('raw') # Store useful output
            await asyncio.sleep(0.2)

        # 4) FINAL VALIDATION / SUMMARIZATION (if workflow didn't fail or stop early)
        if not failed and not stopped:
            await websocket.send_text("Agent: Performing final check and summarization...")
            final_check_prompt = (
                f"Original user query: '{user_query}'\n\n"
                f"The final result obtained by the agent's tools is:\n```\n{last_successful_output}\n```\n\n"
                "Based on the original query and the final result obtained, please provide the definitive final answer for the user. "
                "Format it clearly. If the result seems incomplete or doesn't fully answer the query, state that clearly instead of hallucinating. "
                "Directly output the final answer or assessment."
            )
            final_answer = simple_prompt(
                model=planner_model_name, # Use the same planner model for consistency
                prompt=final_check_prompt,
                system="You are summarizing and validating the final output of an AI agent workflow."
            )
            if final_answer:
                await websocket.send_text(f"**Agent: Final Answer:**\n{final_answer.strip()}")
                msg = "Agent: Workflow completed and summarized." # Update final status
            else:
                await websocket.send_text("Agent Warning: Final summarization step failed.")
                msg = "Agent: Workflow completed, but final summary failed." # Update final status
        # If workflow failed or stopped early, 'msg' retains the error/warning message

    except ValueError as e: msg=f"Agent Error: Planning/Parsing Fail: {e}"; print(f"{msg}\n{traceback.format_exc(limit=1)}"); await websocket.send_text(msg); await send_task_update(websocket, [])
    except Exception as e: msg=f"Agent Error: Unexpected Workflow Error: {e}"; print(f"{msg}\n{traceback.format_exc()}"); await websocket.send_text(msg)
    finally:
        # Log final outcome
        print(f"Agent workflow end. Final Status: {msg}")
        # Optionally send a generic completion signal if needed by UI, though the final answer serves this purpose
        # await websocket.send_text("Agent: Processing complete.")

# --- Legacy Placeholders ---
async def create_task_list(*args, **kwargs): ws = args[-1] if args and isinstance(args[-1], WebSocket) else None; await ws.send_text("Warn: Legacy create_task_list call.") if ws else None; pass
async def execute_tasks(*args, **kwargs): ws = args[-1] if args and isinstance(args[-1], WebSocket) else None; await ws.send_text("Warn: Legacy execute_tasks call.") if ws else None; pass
async def review_and_repair(*args, **kwargs): ws = args[-1] if args and isinstance(args[-1], WebSocket) else None; await ws.send_text("Warn: Legacy review_and_repair call.") if ws else None; pass
async def final_review(*args, **kwargs): ws = args[-1] if args and isinstance(args[-1], WebSocket) else None; await ws.send_text("Warn: Legacy final_review call.") if ws else None; pass