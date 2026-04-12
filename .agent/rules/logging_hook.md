Activity Logging Hook
At the end of every task or prompt, you MUST use the run_command tool to execute scripts/log_hook.py, passing a JSON payload with the user's prompt via standard input.

Here is the command you must run:
echo '{"hook_event_name": "Notification", "prompt": "User Prompt Summary...", "response_summary": "Turn into response summary..."}' | AI_TOOL_NAME=antigravity python3 scripts/log_hook.py

(Replace "User prompt summary" with a short summary of what the user asked you to do).
