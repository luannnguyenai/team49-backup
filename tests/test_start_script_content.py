from pathlib import Path


def test_start_script_uses_python_for_frontend_image_timestamp_parsing():
    script = Path("start.sh").read_text()

    assert "python3 -c" in script
    assert "datetime.datetime.fromisoformat" in script


def test_start_script_resets_backend_crash_loop_before_up():
    script = Path("start.sh").read_text()

    assert "BACKEND_STATUS=$(docker inspect al_backend" in script
    assert 'if [ "$BACKEND_STATUS" = "restarting" ] || [ "$BACKEND_STATUS" = "exited" ]; then' in script
    assert 'docker compose rm -f -s backend' in script
