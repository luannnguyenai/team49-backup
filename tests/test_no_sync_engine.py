"""
tests/test_no_sync_engine.py
----------------------------
RED phase: Verify codebase không còn sync SQLAlchemy engine.
Sau khi remove sync engine khỏi store.py, các test này phải PASS.
"""
import ast
import pathlib
import pytest


def _get_python_files(root: str = "src") -> list[pathlib.Path]:
    return list(pathlib.Path(root).rglob("*.py"))


def test_no_create_engine_sync_in_src():
    """
    Không file nào trong src/ được import create_engine (sync).
    Chỉ create_async_engine được phép.
    """
    violations: list[str] = []
    for filepath in _get_python_files("src"):
        try:
            source = filepath.read_text(encoding="utf-8")
            tree = ast.parse(source)
        except (SyntaxError, UnicodeDecodeError):
            continue

        for node in ast.walk(tree):
            # from sqlalchemy import create_engine
            if isinstance(node, ast.ImportFrom):
                imported_names = [alias.name for alias in node.names]
                if "create_engine" in imported_names and node.module and "async" not in node.module:
                    violations.append(f"{filepath}:{node.lineno} — imports sync create_engine")
            # import sqlalchemy; sqlalchemy.create_engine(...)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "sqlalchemy":
                        # Can't easily detect usage here, skip import-level check
                        pass

    assert violations == [], "\n".join(violations)


def test_no_sessionmaker_sync_in_src():
    """
    Không file nào trong src/ được dùng sessionmaker (sync) với bind=engine.
    async_sessionmaker là OK.
    """
    violations: list[str] = []
    for filepath in _get_python_files("src"):
        try:
            source = filepath.read_text(encoding="utf-8")
            tree = ast.parse(source)
        except (SyntaxError, UnicodeDecodeError):
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                imported_names = [alias.name for alias in node.names]
                # sessionmaker (not async_sessionmaker) from sqlalchemy.orm
                if (
                    "sessionmaker" in imported_names
                    and "async_sessionmaker" not in imported_names
                    and node.module
                    and "async" not in node.module
                ):
                    violations.append(f"{filepath}:{node.lineno} — imports sync sessionmaker")

    assert violations == [], "\n".join(violations)


def test_store_py_has_no_sync_engine():
    """
    store.py cụ thể không được có SessionLocal hay create_engine.
    """
    store_path = pathlib.Path("src/models/store.py")
    assert store_path.exists(), "store.py không tồn tại"
    source = store_path.read_text(encoding="utf-8")

    assert "SessionLocal" not in source, "store.py vẫn còn SessionLocal (sync)"
    assert "create_engine" not in source, "store.py vẫn còn create_engine (sync)"


def test_get_db_function_removed():
    """
    get_db() (sync dependency) không còn trong store.py.
    """
    store_path = pathlib.Path("src/models/store.py")
    source = store_path.read_text(encoding="utf-8")
    assert "def get_db" not in source, "store.py vẫn còn get_db() sync dependency"
