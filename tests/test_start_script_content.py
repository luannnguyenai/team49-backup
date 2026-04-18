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


def test_start_script_resets_frontend_when_rebuilding_dependencies():
    script = Path("start.sh").read_text()

    assert "FRONTEND_STATUS=$(docker inspect al_frontend" in script
    assert 'docker compose rm -f -s frontend' in script
    assert 'elif [ "$NEED_FRONTEND_REBUILD" = true ]; then' in script


def test_start_script_resets_frontend_on_force_rebuild():
    script = Path("start.sh").read_text()

    assert 'if [ "$FORCE_REBUILD" = true ]; then' in script
    assert 'docker compose rm -f -s frontend' in script
