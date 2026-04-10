import sys
import re
import subprocess
import tempfile
import os
import logging
import resource

logger = logging.getLogger("CodeSandbox")

# Blocklist of dangerous imports/calls that should never run
BLOCKED_PATTERNS = [
    r"\bos\.system\b",
    r"\bos\.popen\b",
    r"\bsubprocess\b",
    r"\bshutil\.rmtree\b",
    r"\bopen\s*\(.*['\"]w['\"]",   # file writes
    r"\bsocket\b",
    r"\burllib\b",
    r"\brequests\b",
    r"\bhttpx\b",
    r"\beval\s*\(",
    r"\bexec\s*\(",
    r"\b__import__\s*\(",
    r"\bimportlib\b",
    r"\bctl\b",
    r"\bpickle\b",
]

def _is_safe_code(code: str) -> tuple[bool, str]:
    """Returns (is_safe, reason) after checking code against blocklist."""
    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, code):
            return False, f"Blocked pattern detected: `{pattern}`"
    return True, ""

def _set_resource_limits():
    """Called in child process to restrict CPU time and open file descriptors.
    Note: RLIMIT_AS (virtual memory) is intentionally omitted because numpy/scipy
    use mmap for loading shared libraries which conflicts with strict AS limits.
    Thread bombing is mitigated via OPENBLAS_NUM_THREADS env variable instead."""
    # Max CPU time: 12 seconds (soft), 15 seconds (hard)
    resource.setrlimit(resource.RLIMIT_CPU, (12, 15))
    # Max open file descriptors: 50 (prevents fork bombs and excessive file I/O)
    resource.setrlimit(resource.RLIMIT_NOFILE, (50, 50))

def run_python_code(code: str, timeout: int = 15) -> str:
    """
    Executes Python code in a restricted sandbox (subprocess).
    Returns printed stdout/stderr output.
    Pre-installed: numpy, sympy, scipy, pandas.

    Safety measures:
    - Static analysis blocklist (blocks network, file writes, subprocess, eval, etc.)
    - CPU time limit via RLIMIT_CPU (12s soft / 15s hard)
    - File descriptor limit via RLIMIT_NOFILE (50 max)
    - Thread limit via OPENBLAS_NUM_THREADS=1 env variable
    - Wall-clock timeout via subprocess.run(timeout=...)
    """
    is_safe, reason = _is_safe_code(code)
    if not is_safe:
        logger.warning(f"Blocked unsafe code: {reason}")
        return f"ExitCode:1\nError: Code was blocked by security policy.\nReason: {reason}"

    temp_path = None
    try:
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
            f.write(code)
            temp_path = f.name

        logger.info("Executing Python code in restricted sandbox...")

        # Inject safe env: limit BLAS/OpenMP threads to prevent thread bombing
        sandbox_env = os.environ.copy()
        sandbox_env["OPENBLAS_NUM_THREADS"] = "1"
        sandbox_env["OMP_NUM_THREADS"] = "1"
        sandbox_env["MKL_NUM_THREADS"] = "1"

        result = subprocess.run(
            [sys.executable, temp_path],
            capture_output=True,
            text=True,
            timeout=timeout,
            env=sandbox_env,
            preexec_fn=_set_resource_limits,
        )
        os.remove(temp_path)

        # --- Structured exit code check ---
        output = ""
        if result.stdout:
            output += f"Output:\n{result.stdout}\n"
        if result.stderr:
            output += f"Stderr:\n{result.stderr}\n"

        if not output.strip():
            return "ExitCode:0\nCode executed successfully but produced no output. Use print() to show results."

        prefix = f"ExitCode:{result.returncode}\n"
        return prefix + output

    except subprocess.TimeoutExpired:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)
        return "ExitCode:1\nError: Execution timed out (15s limit exceeded)."
    except Exception as e:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)
        return f"ExitCode:1\nError: {str(e)}"
