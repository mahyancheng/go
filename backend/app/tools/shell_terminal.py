import subprocess
import asyncio

async def run_command(command: str) -> str:
    """
    Executes a shell command and returns its output or error.
    """
    def _run():
        try:
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
        except Exception as e:
            return f"Shell command execution failed: {e}"
        output = (result.stdout or "") + (result.stderr or "")
        output = output.strip()
        if not output:
            output = f"Command executed (exit code {result.returncode}) with no output."
        return output

    return await asyncio.to_thread(_run)
