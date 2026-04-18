import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


def _load_sync_module():
    module_path = (
        Path(__file__).resolve().parent.parent / "scripts" / "sync_codex_transcript.py"
    )
    spec = importlib.util.spec_from_file_location("sync_codex_transcript", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class SyncCodexTranscriptTests(unittest.TestCase):
    def setUp(self):
        self.module = _load_sync_module()

    def _write_jsonl(self, path: Path, rows: list[dict]):
        with path.open("w", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    def test_extracts_user_prompt_entries_from_codex_transcript(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            transcript_path = Path(tmpdir) / "rollout.jsonl"
            self._write_jsonl(
                transcript_path,
                [
                    {
                        "timestamp": "2026-04-18T06:00:00.000Z",
                        "type": "session_meta",
                        "payload": {
                            "id": "session-123",
                            "cwd": "/repo",
                            "model_provider": "openai",
                        },
                    },
                    {
                        "timestamp": "2026-04-18T06:01:00.000Z",
                        "type": "turn_context",
                        "payload": {"model": "gpt-5.4"},
                    },
                    {
                        "timestamp": "2026-04-18T06:01:05.000Z",
                        "type": "event_msg",
                        "payload": {
                            "type": "user_message",
                            "message": "refactor login flow",
                        },
                    },
                    {
                        "timestamp": "2026-04-18T06:02:00.000Z",
                        "type": "event_msg",
                        "payload": {"type": "task_complete"},
                    },
                ],
            )

            entries = self.module.extract_codex_entries_from_transcript(
                transcript_path=transcript_path,
                repo="A20-App-049",
                branch="rin/refactor",
                commit="abc1234",
                student="student@example.com",
            )

            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0]["tool"], "codex")
            self.assertEqual(entries[0]["event"], "UserPromptSubmit")
            self.assertEqual(entries[0]["session_id"], "session-123")
            self.assertEqual(entries[0]["model"], "gpt-5.4")
            self.assertEqual(entries[0]["prompt"], "refactor login flow")
            self.assertEqual(entries[0]["repo"], "A20-App-049")
            self.assertEqual(entries[0]["branch"], "rin/refactor")
            self.assertEqual(entries[0]["commit"], "abc1234")

    def test_sync_transcript_appends_only_missing_entries(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            transcript_path = Path(tmpdir) / "rollout.jsonl"
            log_path = Path(tmpdir) / "session.jsonl"
            self._write_jsonl(
                transcript_path,
                [
                    {
                        "timestamp": "2026-04-18T06:00:00.000Z",
                        "type": "session_meta",
                        "payload": {"id": "session-123", "cwd": "/repo"},
                    },
                    {
                        "timestamp": "2026-04-18T06:01:00.000Z",
                        "type": "turn_context",
                        "payload": {"model": "gpt-5.4"},
                    },
                    {
                        "timestamp": "2026-04-18T06:01:05.000Z",
                        "type": "event_msg",
                        "payload": {"type": "user_message", "message": "prompt one"},
                    },
                    {
                        "timestamp": "2026-04-18T06:02:05.000Z",
                        "type": "event_msg",
                        "payload": {"type": "user_message", "message": "prompt two"},
                    },
                ],
            )
            self._write_jsonl(
                log_path,
                [
                    {
                        "tool": "codex",
                        "event": "UserPromptSubmit",
                        "session_id": "session-123",
                        "prompt": "prompt one",
                        "turn_id": "2026-04-18T06:01:05.000Z",
                        "transcript_path": str(transcript_path),
                    }
                ],
            )

            appended = self.module.sync_transcript_to_log(
                transcript_path=transcript_path,
                log_path=log_path,
                repo="A20-App-049",
                branch="rin/refactor",
                commit="abc1234",
                student="student@example.com",
            )

            self.assertEqual(appended, 1)
            lines = log_path.read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(lines), 2)
            last = json.loads(lines[-1])
            self.assertEqual(last["prompt"], "prompt two")
            self.assertEqual(last["turn_id"], "2026-04-18T06:02:05.000Z")


if __name__ == "__main__":
    unittest.main()
