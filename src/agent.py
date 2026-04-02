"""
Basic agent loop using the Anthropic Claude API.
Receives user input, calls tools as needed, and returns results.
"""

import logging
from anthropic import Anthropic
from .config import ANTHROPIC_API_KEY, DEFAULT_MODEL, LOG_LEVEL
from .tools import get_tool_schemas, execute_tool

logging.basicConfig(level=LOG_LEVEL, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an intelligent AI assistant.
You can use the provided tools to complete tasks.
Think step by step and use tools when necessary."""


def create_agent():
    """Create an agent with the Anthropic client."""
    if not ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY is not configured. Check your .env file")
    return Anthropic(api_key=ANTHROPIC_API_KEY)


def run_agent_loop(client: Anthropic, user_input: str, max_turns: int = 10) -> str:
    """
    Run the agent loop: send message -> receive response -> call tool -> repeat.

    Args:
        client: Anthropic client
        user_input: User's question or request
        max_turns: Maximum number of tool-calling turns

    Returns:
        The agent's final response
    """
    messages = [{"role": "user", "content": user_input}]
    tools = get_tool_schemas()

    for turn in range(max_turns):
        logger.info(f"Turn {turn + 1}/{max_turns}")

        response = client.messages.create(
            model=DEFAULT_MODEL,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=tools,
            messages=messages,
        )

        # If agent stops (no more tool calls)
        if response.stop_reason == "end_turn":
            final_text = ""
            for block in response.content:
                if hasattr(block, "text"):
                    final_text += block.text
            return final_text

        # Handle tool calls
        tool_results = []
        has_tool_use = False

        for block in response.content:
            if block.type == "tool_use":
                has_tool_use = True
                logger.info(f"Calling tool: {block.name}({block.input})")
                result = execute_tool(block.name, block.input)
                logger.info(f"Result: {result[:200]}")
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result,
                })

        if not has_tool_use:
            # No tool calls, return text
            final_text = ""
            for block in response.content:
                if hasattr(block, "text"):
                    final_text += block.text
            return final_text

        # Add assistant response and tool results to messages
        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": tool_results})

    return "Agent reached the maximum number of processing turns."


def main():
    """Interactive loop - enter a prompt and receive results."""
    client = create_agent()
    print("Agentic App (type 'quit' to exit)")
    print("-" * 50)

    while True:
        user_input = input("\nYou: ").strip()
        if not user_input or user_input.lower() in ("quit", "exit", "q"):
            print("Bye!")
            break

        try:
            response = run_agent_loop(client, user_input)
            print(f"\nAgent: {response}")
        except Exception as e:
            logger.error(f"Error: {e}")
            print(f"\nError: {e}")


if __name__ == "__main__":
    main()
