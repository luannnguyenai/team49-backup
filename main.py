"""
main.py — Application entry point.
Run: python main.py  OR  uvicorn src.api.app:app --reload
"""

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "src.api.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
