# backend/app/tools/shell_terminal.py
import subprocess
import shlex
import asyncio
import traceback

ALLOWED_COMMANDS = {'ls', 'pwd', 'echo', 'cat', 'grep', 'mkdir', 'rmdir', 'touch', 'head', 'tail', 'date'}
TIMEOUT_SECONDS = 15

async def execute_shell_command(full_command: str, websocket) -> str:
    await websocket.send_text(f"Agent: Preparing shell: {full_command[:50]}...")
    print(f"Attempting shell command: {full_command}")
    try: command_parts = shlex.split(full_command)
    except ValueError as e: error_msg = f"Error parsing command: {e}"; await websocket.send_text(f"Agent Error: {error_msg}"); print(error_msg); return error_msg
    if not command_parts: await websocket.send_text("Agent Error: Empty command."); return "Error: Empty command."
    command = command_parts[0]; args = command_parts[1:]
    if command not in ALLOWED_COMMANDS: error_msg = f"Error: Command '{command}' not allowed."; await websocket.send_text(f"Agent Error: {error_msg}"); print(error_msg); return error_msg
    for arg in args:
        if not all(c.isalnum() or c in (' ','-','_','.','/') for c in arg) or '..' in arg:
             if any(c in arg for c in ";|&`$()<>*?[]{}!\\"): error_msg = f"Error: Unsafe arg '{arg}'"; await websocket.send_text(f"Agent Error: {error_msg}"); print(error_msg); return error_msg
    try:
        exec_command = [command] + args
        await websocket.send_text(f"Agent: Running: {' '.join(exec_command)}")
        print(f"Executing safe command (executor): {exec_command}")
        loop = asyncio.get_running_loop()
        proc = await loop.run_in_executor(None, lambda: subprocess.run(exec_command, capture_output=True, text=True, timeout=TIMEOUT_SECONDS, check=False, shell=False, encoding='utf-8'))
        exit_code = proc.returncode; output = proc.stdout or ""; error_output = proc.stderr or ""
        print(f"Shell finished: exit={exit_code}")
        result = f"Exit Code: {exit_code}\n";
        if output: result += f"Output:\n{output}\n"
        if error_output: result += f"Errors:\n{error_output}\n"
        await websocket.send_text(f"Agent: Shell finished (Exit: {exit_code}).")
        return result.strip()
    except subprocess.TimeoutExpired: await websocket.send_text(f"Agent Error: Timeout"); print(f"Timeout: {full_command}"); return f"Error: Timeout."
    except FileNotFoundError: error_msg = f"Error: Cmd '{command}' not found."; await websocket.send_text(f"Agent Error: {error_msg}"); print(error_msg); return error_msg
    except PermissionError as e: error_msg = f"Error: Permission denied for '{command}': {e}"; await websocket.send_text(f"Agent Error: {error_msg}"); print(error_msg); return error_msg
    except Exception as e: error_msg = f"Error executing shell '{full_command}': {e}"; await websocket.send_text(f"Agent Error: {error_msg}"); print(error_msg); traceback.print_exc(); return error_msg
