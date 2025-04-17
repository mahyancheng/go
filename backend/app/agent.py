# backend/app/agent.py
import os
import datetime
import asyncio
import traceback # For detailed error logging
import json
import re # For robust list parsing

# Adjust this import based on llm_handler.py location
# Assumes agent.py is in 'app' directory
try:
    from .llm_handler import send_prompt, PLANNING_TOOLING_MODEL, DEEPCODER_MODEL
except ImportError:
    # Fallback if agent.py is directly in 'backend'
    from llm_handler import send_prompt, PLANNING_TOOLING_MODEL, DEEPCODER_MODEL

# --- Import the ACTUAL tool functions with detailed error logging ---

# --- Code Interpreter ---
try:
    from .tools.code_interpreter import execute_python_code as execute_python_code_impl
except ImportError as e:
    print("Warning: Could not import execute_python_code_impl from tools.code_interpreter.")
    print("--- Full Import Traceback (agent.py -> execute_python_code_impl) ---"); traceback.print_exc(); print("--- End Traceback ---")
    # *** CORRECTLY INDENTED PLACEHOLDER ***
    async def execute_python_code_impl(code_details, websocket):
        # This block is indented under 'except ImportError'
        await websocket.send_text("Agent Warning: execute_python_code tool not implemented due to import error.")
        return "Error: Python code execution tool failed to import."
except Exception as e:
     print(f"Warning: Unexpected error importing execute_python_code_impl: {e}"); traceback.print_exc()
     # *** CORRECTLY INDENTED PLACEHOLDER ***
     async def execute_python_code_impl(code_details, websocket):
         # This block is indented under 'except Exception'
         await websocket.send_text("Agent Warning: execute_python_code tool not implemented due to unexpected import error.")
         return "Error: Python code execution tool failed to import unexpectedly."

# --- Shell Terminal ---
try:
    from .tools.shell_terminal import execute_shell_command as execute_shell_command_impl
except ImportError as e:
    print("Warning: Could not import execute_shell_command_impl from tools.shell_terminal.")
    print("--- Full Import Traceback (agent.py -> execute_shell_command_impl) ---"); traceback.print_exc(); print("--- End Traceback ---")
    # *** CORRECTLY INDENTED PLACEHOLDER ***
    async def execute_shell_command_impl(command_details, websocket):
        # This block is indented under 'except ImportError'
        await websocket.send_text("Agent Warning: execute_shell_command tool not implemented due to import error.")
        return "Error: Shell command execution tool failed to import."
except Exception as e:
     print(f"Warning: Unexpected error importing execute_shell_command_impl: {e}"); traceback.print_exc()
     # *** CORRECTLY INDENTED PLACEHOLDER ***
     async def execute_shell_command_impl(command_details, websocket):
         # This block is indented under 'except Exception'
         await websocket.send_text("Agent Warning: execute_shell_command tool not implemented due to unexpected import error.")
         return "Error: Shell command execution tool failed to import unexpectedly."


# --- Browser Integration ---
try:
    from .tools.browseruse_integration import browse_website as browse_website_impl
except ImportError as e:
    print("Warning: Could not import browse_website_impl from tools.browseruse_integration.")
    print("--- Full Import Traceback (agent.py -> browse_website_impl) ---"); traceback.print_exc(); print("--- End Traceback ---")
    # *** CORRECTLY INDENTED PLACEHOLDER ***
    async def browse_website_impl(browse_details, websocket):
        # This block is indented under 'except ImportError'
        await websocket.send_text("Agent Warning: browse_website tool not implemented due to import error.")
        return "Error: Browser interaction tool failed to import."
except Exception as e:
     print(f"Warning: Unexpected error importing browse_website_impl: {e}"); traceback.print_exc()
     # *** CORRECTLY INDENTED PLACEHOLDER ***
     async def browse_website_impl(browse_details, websocket):
         # This block is indented under 'except Exception'
         await websocket.send_text("Agent Warning: browse_website tool not implemented due to unexpected import error.")
         return "Error: Browser interaction tool failed to import unexpectedly."

# --- REMOVED Firecrawl Imports ---


# --- Tool Wrapper Functions (CALL the imported implementations) ---
async def execute_python_code(code_details, websocket):
    await websocket.send_text("Agent: Executing Python code...")
    print(f"Executing code: {str(code_details)[:100]}...")
    result = await execute_python_code_impl(code_details, websocket)
    return result

async def execute_shell_command(command_details, websocket):
    await websocket.send_text("Agent: Executing shell command...")
    print(f"Executing shell command: {command_details}")
    result = await execute_shell_command_impl(command_details, websocket)
    return result

async def browse_website(browse_details, websocket):
    await websocket.send_text("Agent: Browsing website...")
    print(f"Browsing action: {browse_details}")
    result = await browse_website_impl(browse_details, websocket)
    return result

# --- REMOVED scrape/crawl wrappers ---


# --- Directory for Tasks ---
TASK_DIR = os.path.join(os.path.dirname(__file__), "..", "tasks") # Assumes tasks dir is sibling to app dir
if not os.path.isdir(TASK_DIR): # Check if it's a directory before trying to create
    try:
        os.makedirs(TASK_DIR)
        print(f"Created task directory: {TASK_DIR}")
    except OSError as e:
        print(f"Warning: Could not create task directory at {TASK_DIR}. Using fallback. Error: {e}")
        TASK_DIR = os.path.join(os.path.dirname(__file__), "tasks") # Fallback inside app
        os.makedirs(TASK_DIR, exist_ok=True)
print(f"Using task directory: {TASK_DIR}")

# --- Main Agent Workflow Handler ---
async def handle_agent_workflow(user_query: str, selected_model: str, websocket): # Takes actual websocket now
    task_file_path = None; start_time = datetime.datetime.now(); print(f"[{start_time.strftime('%H:%M:%S')}] Workflow start: {user_query[:50]}...")
    try:
        await websocket.send_text("Agent: Processing request...")
        planning_model = PLANNING_TOOLING_MODEL
        await websocket.send_text(f"Agent: Creating task list using {planning_model}...")
        task_file_path = await create_task_list(user_query, planning_model, websocket); await websocket.send_text(f"Agent: Task list created: {os.path.basename(task_file_path)}")
        await websocket.send_text(f"Agent: Executing tasks (Review LLM: {selected_model})...")
        await execute_tasks(task_file_path, selected_model, websocket)
        review_model = PLANNING_TOOLING_MODEL
        await websocket.send_text(f"Agent: Final review (LLM: {review_model})...")
        final_response = await final_review(task_file_path, user_query, review_model, websocket)
        await websocket.send_text(f"Agent: Final Response: {final_response}")
    except Exception as e: error_msg = f"Workflow error: {e}"; print(error_msg); traceback.print_exc(); await websocket.send_text(f"Agent Error: {error_msg}")
    finally: end_time = datetime.datetime.now(); duration = end_time - start_time; print(f"[{end_time.strftime('%H:%M:%S')}] Workflow finished in {duration.total_seconds():.2f}s."); await websocket.send_text(f"Agent: Workflow complete.")

# --- create_task_list ---
async def create_task_list(user_input: str, model_to_use: str, websocket) -> str:
    await websocket.send_text("Agent: Requesting task list..."); print(f"Creating task list using {model_to_use}...")
    # Use stricter prompt without scraper
    system_message = """You are a planning agent. Your goal is to break down the user's request into a sequence of actionable tasks.
Each task must be achievable by one of the available tools: code_interpreter, shell_terminal, browser.

**CRITICAL:** Your output MUST be *ONLY* a markdown numbered list with checkboxes, starting directly with '1. [ ]'.
- Do NOT include any introductory text like "Okay, here is the task list:".
- Do NOT include any explanations or concluding remarks.
- Do NOT include markdown code blocks like ```markdown ... ```.
- Only output the list items themselves.

Example Output:
1. [ ] Use the browser to search for information about current AI trends.
2. [ ] Use the code_interpreter to analyze the data and identify the top 3 trends.
3. [ ] Use the shell_terminal to save the analysis results to a file named 'trends.txt'."""
    prompt = f"Based on the user request: '{user_input}', create the task list following the strict formatting rules."
    task_list_md = send_prompt(model_name=model_to_use, prompt=prompt, system_message=system_message)
    if task_list_md is None: raise ValueError("LLM communication failed for task list.")
    # Robust Parsing Logic
    cleaned_task_list_md = ""; extracted_lines = []
    list_item_pattern = re.compile(r"^\s*(\d+\.|[-*])\s*\[\s*\]\s*.*")
    in_list = False; lines = task_list_md.strip().splitlines()
    for line in lines:
        line_stripped = line.strip()
        if list_item_pattern.match(line_stripped): extracted_lines.append(line); in_list = True
        elif in_list and line_stripped == "": continue # Allow blank lines within list
        elif in_list: break # Stop if non-list item found after list started
    if extracted_lines: cleaned_task_list_md = "\n".join(extracted_lines)
    # End of Parsing Logic
    if not cleaned_task_list_md: print(f"Error: Could not extract task list from LLM response. Raw:\n{task_list_md}"); raise ValueError("LLM produced invalid task list format or no list found.")
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S"); safe_filename_base = "".join(c if c.isalnum() or c in (' ','_','-') else '_' for c in user_input[:30]).rstrip()
    safe_filename = f"tasks_{safe_filename_base}_{timestamp}.md"; file_path = os.path.join(TASK_DIR, safe_filename)
    try:
        with open(file_path, "w", encoding="utf-8") as f: f.write(cleaned_task_list_md)
        print(f"Task list saved: {file_path}"); await websocket.send_text(f"Agent: Task list saved.")
        return file_path
    except IOError as e: await websocket.send_text(f"Agent Error: Cannot save task list: {e}"); print(f"IOError saving task list: {e}"); raise e

# --- execute_tasks ---
async def execute_tasks(task_file_path: str, model_to_use_for_review: str, websocket):
    print(f"Executing tasks from: {task_file_path} using {model_to_use_for_review} for review")
    if not os.path.exists(task_file_path): raise FileNotFoundError(f"Task file not found: {task_file_path}")
    try:
        with open(task_file_path, "r+", encoding="utf-8") as f:
            lines = f.readlines(); f.seek(0); all_tasks_ok = True
            for i, line in enumerate(lines):
                original_line = line; line_stripped = line.strip(); is_incomplete = False; task_prefix = ""
                # Corrected check for list item format
                if line_stripped.startswith(("- [ ]", "* [ ]")): is_incomplete = True; task_prefix = line_stripped.split("]", 1)[0] + "] "
                elif ". [ ]" in line_stripped:
                     parts = line_stripped.split(". [ ]", 1)
                     if len(parts) > 0 and parts[0].isdigit(): is_incomplete = True; task_prefix = parts[0] + ". [ ] "

                if is_incomplete:
                    try: task_desc = line_stripped.split("]", 1)[1].strip()
                    except IndexError: await websocket.send_text(f"Agent Warning: Skipping malformed task {i+1}"); lines[i] = original_line; all_tasks_ok = False; continue
                    await websocket.send_text(f"Agent: Starting task {i+1}: {task_desc}"); print(f"Processing task {i+1}: {task_desc}")
                    tool_name, tool_input = "unknown", task_desc
                    try: # Tool Selection with enhanced parsing
                        # Using the strict prompt
                        tool_selection_prompt = f"""Analyze the task below. Determine the single best tool and input.
Available tools and their purpose:
- code_interpreter: Executes general Python code provided as input. *Do not use this for browsing.*
- shell_terminal: Executes safe, whitelisted shell commands provided as input.
- browser: Performs actions within a web browser based on natural language instructions (e.g., navigating, clicking, searching, inputting text). Input should be the specific instruction for the browser action. *Use this for all web navigation, searching, and interaction tasks.*
- none: Use this if no tool action is required for the task (e.g., the task is just planning or analysis).

Task: '{task_desc}'

Respond ONLY with a valid JSON object like this: {{"tool_name": "...", "tool_input": "..."}}

**DO NOT add ANY introductory text, explanations, or markdown formatting like ```json. Just the raw JSON object.**

Example Response for browsing/searching task:
{{"tool_name": "browser", "tool_input": "Search for 'latest AI research papers' on Google and find the title of the first result."}}
Example Response for specific URL navigation:
{{"tool_name": "browser", "tool_input": "Go to [https://www.bbc.com/news](https://www.bbc.com/news)"}}
Example Response for coding task:
{{"tool_name": "code_interpreter", "tool_input": "def greet(name):\\n print(f'Hello, {{name}}!')\\ngreet('World')"}}

Valid JSON response:"""
                        raw_resp = send_prompt(PLANNING_TOOLING_MODEL, tool_selection_prompt)
                        # Enhanced JSON Parsing Logic
                        json_str_to_parse = None
                        if raw_resp:
                            match_json = re.search(r"```json\s*(\{.*?\})\s*```", raw_resp, re.DOTALL | re.IGNORECASE);
                            if match_json: json_str_to_parse = match_json.group(1).strip(); print("Found JSON block using ```json")
                            else:
                                match_generic = re.search(r"```\s*(\{.*?\})\s*```", raw_resp, re.DOTALL);
                                if match_generic: json_str_to_parse = match_generic.group(1).strip(); print("Found JSON block using ```")
                                else: json_start = raw_resp.find('{'); json_end = raw_resp.rfind('}') + 1;
                                if json_start != -1 and json_end > json_start: json_str_to_parse = raw_resp[json_start:json_end].strip(); print("Found JSON block using first/last braces")
                        if json_str_to_parse:
                            # This 'try' block is for parsing the extracted JSON string
                            try:
                                resp_json = json.loads(json_str_to_parse); tool_name = resp_json.get("tool_name", "unknown").strip(); tool_input = resp_json.get("tool_input", task_desc)
                                # *** THIS 'if' IS CORRECTLY INDENTED under 'try' ***
                                if tool_name not in ["code_interpreter", "shell_terminal", "browser", "none"]:
                                    print(f"Warning: Parsed unknown tool name '{tool_name}' from JSON: {json_str_to_parse}")
                                    tool_name = "unknown"
                            except (json.JSONDecodeError, ValueError) as e:
                                # *** THIS 'except' IS CORRECTLY INDENTED to match 'try' ***
                                await websocket.send_text(f"Agent Warning: Could not parse extracted JSON: {e}")
                                print(f"Warning: Bad JSON after extraction. Extracted: '{json_str_to_parse}'. Raw: {raw_resp[:200]}...");
                                tool_name = "unknown"
                        else:
                            # This 'else' block is indented under 'if json_str_to_parse:'
                            await websocket.send_text(f"Agent Warning: No JSON structure found.")
                            print(f"Warning: No JSON structure found. Raw: {raw_resp[:200]}...");
                            tool_name = "unknown"
                    # This 'except' matches the outer 'try' for the whole tool selection block
                    except Exception as e: await websocket.send_text(f"Agent Error: LLM select failed: {e}"); print(f"Error LLM select..."); traceback.print_exc(); tool_name = "unknown"; all_tasks_ok = False; break

                    # Tool Execution block, indented under the 'if is_incomplete:'
                    await websocket.send_text(f"Agent: Tool: {tool_name}, Input: {str(tool_input)[:50]}...")
                    output, err = "Output placeholder", False
                    if tool_name == "none": output = "No tool needed."; await websocket.send_text(f"Agent: {output}")
                    elif tool_name != "unknown":
                        try:
                            if tool_name == "code_interpreter": output = await execute_python_code(tool_input, websocket)
                            elif tool_name == "shell_terminal": output = await execute_shell_command(tool_input, websocket)
                            elif tool_name == "browser": output = await browse_website(tool_input, websocket) # Calls subprocess version
                            out_str = json.dumps(output) if isinstance(output, dict) else str(output)
                            await websocket.send_text(f"Agent: Output (trunc): {out_str[:200]}..."); print(f"Tool '{tool_name}' output (trunc): {out_str[:200]}")
                        except Exception as e: err_msg = f"Tool '{tool_name}' error: {e}"; print(err_msg); traceback.print_exc(); await websocket.send_text(f"Agent Error: {err_msg}"); output = err_msg; err = True; all_tasks_ok = False
                    else: output = "Tool selection failed."; await websocket.send_text(f"Agent Warning: {output}"); all_tasks_ok = False; lines[i] = original_line; continue

                    # Self-Review block, indented under the 'if is_incomplete:'
                    await websocket.send_text(f"Agent: Reviewing task (LLM: {model_to_use_for_review})..."); review = await review_and_repair(task_file_path, i, task_desc, str(output), model_to_use_for_review, websocket); await websocket.send_text(f"Agent: Review: {review}")
                    if "satisfactory" in review.lower() and not err: lines[i] = task_prefix.replace("[ ]", "[x]") + task_desc + "\n"
                    else: all_tasks_ok = False; await websocket.send_text(f"Agent: Task {i+1} failed review. Stopping."); lines[i] = original_line; break
                else: lines[i] = original_line # This 'else' matches 'if is_incomplete:'
            # These lines are indented under the 'with open(...)'
            f.seek(0); f.writelines(lines); f.truncate()
            await websocket.send_text("Agent: Task execution finished.") if all_tasks_ok else await websocket.send_text("Agent: Task execution stopped.")
    # This 'except' matches the outer 'try' of the function
    except Exception as e: error_message = f"Error in task execution loop: {e}"; print(error_message); traceback.print_exc(); await websocket.send_text(f"Agent Error: {error_message}"); raise e

# --- review_and_repair ---
async def review_and_repair(task_file_path: str, task_index: int, task_description: str, task_output: str, model_to_use: str, websocket):
    print(f"Reviewing task {task_index+1} using {model_to_use}"); system_message = """You are a meticulous reviewing agent..."""; task_output_str = str(task_output)[:2000]
    prompt = f"""Original Task: {task_description}\nOutput:\n---\n{task_output_str}\n---\nReview Result (Satisfactory or Issue/Suggestion):"""
    review = send_prompt(model_to_use, prompt, system_message)
    if not review: print("Error: LLM review failed."); await websocket.send_text("Agent Error: LLM review failed."); return "Review failed."
    review = review.strip(); print(f"Review result: {review}")
    if "satisfactory" not in review.lower(): await websocket.send_text(f"Agent: Task {task_index+1} attention. Review: {review}")
    return review

# --- final_review ---
async def final_review(task_file_path: str, original_query: str, model_to_use: str, websocket) -> str:
    # Base indentation for function scope
    await websocket.send_text(f"Agent: Requesting final summary from {model_to_use}...")
    print(f"Performing final review using {model_to_use}...")
    if not os.path.exists(task_file_path):
        raise FileNotFoundError(f"Task file not found for final review: {task_file_path}")

    content = ""
    try:
        # Indented under try
        with open(task_file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except IOError as e:
        # Indented under except
        await websocket.send_text(f"Agent Error: Cannot read task file: {e}")
        print(f"Error reading task file: {e}")
        return f"Error reading task file."

    # =============================================================================
    # <<< START OF CORRECTLY INDENTED BLOCK >>>
    # This block MUST be indented relative to the start of the final_review function definition
    # (Usually 4 spaces relative to the 'async def final_review...' line)
    # Ensure the 's' in 'system_message' aligns with the 'a' in 'await' above the 'try' block
    system_message = """You are a final review and summarization agent. The user had an original request, and a series of tasks were attempted, documented below in the markdown file content.
Synthesize the results *only from successfully completed tasks* (marked with '[x]') into a coherent, final response that directly addresses the original user query.
Ignore tasks marked '[ ]' or tasks that resulted in errors unless the error itself is the answer.
Focus on the final outcome and key findings. Be clear, concise, and directly answer the user's original query based *only* on the provided task outcomes. Do not mention the tasks themselves in the final output unless necessary for clarity."""

    prompt = f"""Original User Query: {original_query}

Task File Content ({os.path.basename(task_file_path)}):
---
{content}
---

Generate the final, user-facing response based *only* on the successfully completed tasks listed above."""
    # <<< END OF CORRECTLY INDENTED BLOCK >>>
    # =============================================================================

    # This line is also part of the main function block, correctly indented
    final_response = send_prompt(model_name=model_to_use, prompt=prompt, system_message=system_message)

    # This block is also part of the function scope, correctly indented
    if not final_response:
        await websocket.send_text("Agent Error: LLM failed final response.")
        print("Error: LLM failed final response.")
        return "Agent Error: Could not generate final response."

    # These lines must also be indented relative to the start of the function
    await websocket.send_text("Agent: Final summary generated.")
    print("Final review complete.")
    return final_response.strip()
