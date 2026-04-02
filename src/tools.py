"""
Tool definitions for the agent.
Add new tools by creating a function and registering it in the TOOLS dict.
"""

import httpx


def search_web(query: str) -> str:
    """Search for information on the web (placeholder)."""
    return f"Search results for: {query}"


def calculate(expression: str) -> str:
    """Evaluate a math expression."""
    try:
        result = eval(expression, {"__builtins__": {}})
        return str(result)
    except Exception as e:
        return f"Error: {e}"


def fetch_url(url: str) -> str:
    """Fetch content from a URL."""
    try:
        resp = httpx.get(url, timeout=10, follow_redirects=True)
        return resp.text[:2000]
    except Exception as e:
        return f"Error: {e}"


# Tool registry - the agent uses this dict
TOOLS = {
    "search_web": {
        "fn": search_web,
        "description": "Search for information on the web",
        "parameters": {"query": "string"},
    },
    "calculate": {
        "fn": calculate,
        "description": "Evaluate a math expression",
        "parameters": {"expression": "string"},
    },
    "fetch_url": {
        "fn": fetch_url,
        "description": "Fetch content from a URL",
        "parameters": {"url": "string"},
    },
}


def get_tool_schemas() -> list[dict]:
    """Return tool schemas in Anthropic API format."""
    schemas = []
    for name, tool in TOOLS.items():
        schemas.append({
            "name": name,
            "description": tool["description"],
            "input_schema": {
                "type": "object",
                "properties": {
                    k: {"type": v, "description": k}
                    for k, v in tool["parameters"].items()
                },
                "required": list(tool["parameters"].keys()),
            },
        })
    return schemas


def execute_tool(name: str, args: dict) -> str:
    """Execute a tool by name."""
    tool = TOOLS.get(name)
    if not tool:
        return f"Tool '{name}' does not exist"
    return tool["fn"](**args)
