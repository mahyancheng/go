import os
import glob
import asyncio
import gradio as gr
import traceback

# Use absolute imports based on the "app" package.
from app.tools.src.browser.custom_browser import CustomBrowser
from app.tools.src.browser.custom_context import BrowserContextConfig
from app.tools.src.controller.custom_controller import CustomController

_global_browser = None
_global_browser_context = None
_global_agent = None

async def run_custom_agent(
        llm,
        use_own_browser,
        keep_browser_open,
        headless,            # Provided but not used by CustomBrowser.
        disable_security,    # Provided but not used by CustomBrowser.
        window_w,
        window_h,
        save_recording_path,
        save_agent_history_path,
        save_trace_path,
        task,
        add_infos,
        max_steps,
        use_vision,
        max_actions_per_step,
        tool_calling_method,
        chrome_cdp,         # Unused.
        max_input_tokens,
        llm_provider,
        llm_model_name,
        llm_num_ctx,
        llm_temperature,
        llm_base_url,
        llm_api_key,
):
    global _global_browser, _global_browser_context, _global_agent

    # Build extra arguments for logging/debugging (not passed to CustomBrowser).
    extra_args = ["--accept_downloads=True", f"--window-size={window_w},{window_h}"]
    if use_own_browser:
        chrome_user_data = os.getenv("CHROME_USER_DATA", None)
        if chrome_user_data:
            extra_args.append(f"--user-data-dir={chrome_user_data}")
    
    # Create a new CustomBrowser instance.
    if _global_browser is None:
        _global_browser = CustomBrowser()
    
    # For window sizing, pass a simple dictionary.
    browser_window_size = {"width": window_w, "height": window_h}
    
    if _global_browser_context is None:
        _global_browser_context = await _global_browser.new_context(
            config=BrowserContextConfig(
                trace_path=save_trace_path if save_trace_path else None,
                save_recording_path=save_recording_path if save_recording_path else None,
                save_downloads_path="./tmp/downloads",
                no_viewport=False,
                browser_window_size=browser_window_size,
            )
        )
    
    # Import CustomAgent and the custom prompt classes.
    from app.tools.src.agent.custom_agent import CustomAgent
    from app.tools.src.agent.custom_prompts import CustomSystemPrompt, CustomAgentMessagePrompt
    controller = CustomController()
    
    if _global_agent is None:
        _global_agent = CustomAgent(
            task=task,
            add_infos=add_infos,
            use_vision=use_vision,
            llm=llm,
            browser=_global_browser,
            browser_context=_global_browser_context,
            controller=controller,
            system_prompt_class=CustomSystemPrompt,
            agent_prompt_class=CustomAgentMessagePrompt,
            page_extraction_llm={},  # Set to empty dict to satisfy validation
            max_actions_per_step=max_actions_per_step,
            tool_calling_method=tool_calling_method,
            max_input_tokens=max_input_tokens,
            generate_gif=True
        )
    history = await _global_agent.run(max_steps=max_steps)
    history_file = os.path.join(save_agent_history_path, f"{_global_agent.state.agent_id}.json")
    _global_agent.save_history(history_file)
    final_result = history.final_result()
    errors = history.errors()
    model_actions = history.model_actions()
    model_thoughts = history.model_thoughts()
    trace_files = glob.glob(os.path.join(save_trace_path, "*.zip")) if save_trace_path else None
    trace_file = trace_files[0] if trace_files else None
    
    # Clean up if the browser is not to be kept open.
    _global_agent = None
    if not keep_browser_open:
        if _global_browser_context:
            await _global_browser_context.close()
            _global_browser_context = None
        if _global_browser:
            await _global_browser.close()
            _global_browser = None
    
    return (
        final_result,
        errors,
        model_actions,
        model_thoughts,
        None,
        trace_file,
        history_file,
        gr.update(value="Stop", interactive=True),
        gr.update(interactive=True)
    )
