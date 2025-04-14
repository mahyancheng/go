import io
import contextlib
import traceback
import asyncio

async def run_code(code: str) -> str:
    """
    Executes Python code and returns output or error trace.
    """
    def _execute():
        stdout = io.StringIO()
        stderr = io.StringIO()
        try:
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                exec(code, {})  # Execute in an empty namespace.
        except Exception:
            return f"Error executing code:\n{traceback.format_exc()}"
        output = stdout.getvalue()
        err_out = stderr.getvalue()
        result = (output + "\n" + err_out).strip()
        if not result:
            return "Code executed successfully with no output."
        return result

    return await asyncio.to_thread(_execute)
