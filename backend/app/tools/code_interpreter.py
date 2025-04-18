# backend/app/tools/code_interpreter.py
import subprocess
import tempfile
import os
import platform
import asyncio
import traceback
import sys

USE_DOCKER = False
DOCKER_IMAGE = "python:3.11-slim-buster"
TIMEOUT_SECONDS = 30

async def execute_python_code_subprocess(code: str, websocket) -> str:
    if USE_DOCKER: return "Subprocess execution skipped (Docker preferred)."
    await websocket.send_text("Agent: Executing code via subprocess...")
    print("Executing code using subprocess.run (in executor).")
    script_path = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as tmp:
            script_path = tmp.name; tmp.write(code)
        py_exec = sys.executable # Use the same python that runs the app
        cmd = [py_exec, script_path]
        await websocket.send_text(f"Agent: Running script {os.path.basename(script_path)}...")
        loop = asyncio.get_running_loop()
        proc = await loop.run_in_executor(None, lambda: subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT_SECONDS, check=False, encoding='utf-8'))
        exit_code = proc.returncode; output = proc.stdout or ""; error_output = proc.stderr or ""
        print(f"Subprocess finished: exit={exit_code}")
        result = f"Exit Code: {exit_code}\n";
        if output: result += f"Output:\n{output}\n"
        if error_output: result += f"Errors:\n{error_output}\n"
        await websocket.send_text(f"Agent: Code finished (Exit: {exit_code}).")
        return result.strip()
    except subprocess.TimeoutExpired: await websocket.send_text(f"Agent Error: Timeout after {TIMEOUT_SECONDS}s."); print("Timeout"); return f"Error: Timeout."
    except FileNotFoundError: await websocket.send_text("Agent Error: Python not found."); print("Python not found."); return "Error: Python interpreter not found."
    except Exception as e: error_msg = f"Error executing Python: {e}"; await websocket.send_text(f"Agent Error: {error_msg}"); print(error_msg); traceback.print_exc(); return error_msg
    finally:
        if script_path and os.path.exists(script_path):
            try: os.remove(script_path)
            except OSError as e: print(f"Warning: Could not remove tmp script {script_path}: {e}")

async def execute_python_code(code: str, websocket) -> str:
    return await execute_python_code_subprocess(code, websocket)