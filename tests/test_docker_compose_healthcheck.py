from pathlib import Path


def test_backend_healthcheck_uses_python_not_curl():
    compose_file = Path("docker-compose.yml").read_text()

    assert 'test:\n        - "CMD"\n        - "python"' in compose_file
    assert '"curl"' not in compose_file
