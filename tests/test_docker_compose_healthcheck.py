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
