import os
from app.llm_handler import LLMHandler
from app.tools.browseruse_integration import run_custom_agent

class Agent:
    """
    This Agent class integrates the custom agent workflow from the repository.
    It sets default parameters (using only the qwen2.5:32b-instruct model) and then calls the custom agent.
    """
    def __init__(self):
        # Default parameters (adjust as needed or load from environment variables)
        self.agent_type = "custom"
        self.llm_provider = "ollama"
        self.llm_model_name = "qwen2.5:32b-instruct"
        self.ollama_num_ctx = 16000
        self.llm_temperature = 0.6
        self.llm_base_url = ""
        self.llm_api_key = ""
        self.use_own_browser = False
        self.keep_browser_open = False
        self.headless = True
        self.disable_security = True
        self.window_w = 1280
        self.window_h = 1100
        self.save_recording_path = "./tmp/record_videos"
        self.save_agent_history_path = "./tmp/agent_history"
        self.save_trace_path = "./tmp/traces"
        self.enable_recording = True
        self.max_steps = 50
        self.use_vision = False
        self.max_actions_per_step = 10
        self.tool_calling_method = "auto"
        self.chrome_cdp = ""
        self.max_input_tokens = 128000
        self.add_infos = ""
        self.task = None

        self.llm = LLMHandler(model_name=self.llm_model_name)
    
    async def process(self, user_query: str) -> str:
        self.task = user_query
        # Call the full custom agent workflow via the integration function.
        (final_result,
         errors,
         model_actions,
         model_thoughts,
         _,
         trace_file,
         history_file,
         stop_button,
         run_button) = await run_custom_agent(
            llm=self.llm,
            use_own_browser=self.use_own_browser,
            keep_browser_open=self.keep_browser_open,
            headless=self.headless,
            disable_security=self.disable_security,
            window_w=self.window_w,
            window_h=self.window_h,
            save_recording_path=self.save_recording_path,
            save_agent_history_path=self.save_agent_history_path,
            save_trace_path=self.save_trace_path,
            task=self.task,
            add_infos=self.add_infos,
            max_steps=self.max_steps,
            use_vision=self.use_vision,
            max_actions_per_step=self.max_actions_per_step,
            tool_calling_method=self.tool_calling_method,
            chrome_cdp=self.chrome_cdp,
            max_input_tokens=self.max_input_tokens,
            llm_provider=self.llm_provider,
            llm_model_name=self.llm_model_name,
            llm_num_ctx=self.ollama_num_ctx,
            llm_temperature=self.llm_temperature,
            llm_base_url=self.llm_base_url,
            llm_api_key=self.llm_api_key,
        )
        return final_result if final_result else errors
