import sys
import subprocess
import tempfile
import os
import logging

logger = logging.getLogger("CodeSandbox")

def run_python_code(code: str, timeout: int = 15) -> str:
    """
    Thực thi mã Python trong Sandbox an toàn (sử dụng tiến trình con).
    Trả về nội dung được in ra (stdout/stderr).
    Hỗ trợ sẵn các thư viện trong virtual environment (numpy, sympy, scipy, pandas).
    """
    try:
        # Create a temporary file to hold the python script
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
            # We import standard data/math libraries to prevent missing imports 
            # if the model forgets to import them, but the model should ideally import them.
            f.write(code)
            temp_path = f.name

        logger.info("Executing Python code sandbox...")
        # Run the script using the current active Python executable from the uv environment
        result = subprocess.run(
            [sys.executable, temp_path],
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        # Clean up the exact script
        os.remove(temp_path)

        output = ""
        if result.stdout:
            output += f"Output:\n{result.stdout}\n"
        if result.stderr:
            output += f"Error:\n{result.stderr}\n"

        if not output.strip():
            return "Code executed successfully but no output was printed. Try using print()."

        return output
    except subprocess.TimeoutExpired:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        return "Lỗi: Timeout. Mã Python mất quá nhiều thời gian để thực thi (giới hạn 15s)."
    except Exception as e:
        if 'temp_path' in locals() and os.path.exists(temp_path):
            os.remove(temp_path)
        return f"Lỗi thực thi mã Python: {str(e)}"
