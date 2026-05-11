from pathlib import Path


def test_backend_healthcheck_uses_python_not_curl():
    compose_file = Path("docker-compose.yml").read_text()

    assert 'test:\n        - "CMD"\n        - "python"' in compose_file
    assert '"curl"' not in compose_file


def test_database_uses_pgvector_image():
    compose_file = Path("docker-compose.yml").read_text()

    assert "image: pgvector/pgvector:pg16" in compose_file


def test_backend_dev_command_scopes_reload_to_src():
    compose_file = Path("docker-compose.yml").read_text()

    assert "--reload --reload-dir src" in compose_file


def test_backend_runs_langgraph_checkpointer_setup_by_default():
    compose_file = Path("docker-compose.yml").read_text()
    env_example = Path(".env.example").read_text()

    assert "AGENT_GRAPH_CHECKPOINTER_SETUP: ${AGENT_GRAPH_CHECKPOINTER_SETUP:-true}" in compose_file
    assert "AGENT_GRAPH_CHECKPOINTER_SETUP=true" in env_example
