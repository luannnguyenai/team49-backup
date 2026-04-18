#!/usr/bin/env python3
"""
Backfill Codex prompt logs from local ~/.codex/sessions transcripts into
the repository .ai-log/session.jsonl file.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_LOG_PATH = REPO_ROOT / ".ai-log" / "session.jsonl"
DEFAULT_SESSIONS_ROOT = Path.home() / ".codex" / "sessions"


def git(cmd: str) -> str:
    try:
        return subprocess.check_output(
            cmd, shell=True, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except Exception:
        return ""


def repo_metadata() -> dict[str, str]:
    return {
        "repo": git("git remote get-url origin").split("/")[-1].replace(".git", ""),
        "branch": git("git rev-parse --abbrev-ref HEAD"),
        "commit": git("git rev-parse --short HEAD"),
        "student": git("git config user.email"),
    }


def parse_ts(raw: str) -> str:
    if not raw:
        return datetime.now(timezone.utc).isoformat()
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).isoformat()
    except ValueError:
        return raw


def load_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    if not path.exists():
        return rows
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def extract_codex_entries_from_transcript(
    *,
    transcript_path: Path,
    repo: str,
    branch: str,
    commit: str,
    student: str,
) -> list[dict]:
    entries: list[dict] = []
    session_id = ""
    model = ""

    for row in load_jsonl(transcript_path):
        row_type = row.get("type")
        payload = row.get("payload", {})

        if row_type == "session_meta":
            session_id = payload.get("id", session_id)
            continue

        if row_type == "turn_context":
            model = payload.get("model", model)
            continue

        if row_type != "event_msg" or payload.get("type") != "user_message":
            continue

        prompt = (payload.get("message") or "").strip()
        if not prompt:
            continue

        entries.append(
            {
                "ts": parse_ts(row.get("timestamp", "")),
                "tool": "codex",
                "event": "UserPromptSubmit",
                "session_id": session_id,
                "model": model,
                "repo": repo,
                "branch": branch,
                "commit": commit,
                "student": student,
                "prompt": prompt[:1000],
                "turn_id": row.get("timestamp", ""),
                "transcript_path": str(transcript_path),
            }
        )

    return entries


def dedupe_key(entry: dict) -> tuple[str, str, str, str, str]:
    return (
        entry.get("tool", ""),
        entry.get("event", ""),
        entry.get("session_id", ""),
        entry.get("turn_id", ""),
        entry.get("prompt", ""),
    )


def sync_transcript_to_log(
    *,
    transcript_path: Path,
    log_path: Path,
    repo: str,
    branch: str,
    commit: str,
    student: str,
) -> int:
    entries = extract_codex_entries_from_transcript(
        transcript_path=transcript_path,
        repo=repo,
        branch=branch,
        commit=commit,
        student=student,
    )
    if not entries:
        return 0

    existing = {dedupe_key(row) for row in load_jsonl(log_path)}
    pending = [entry for entry in entries if dedupe_key(entry) not in existing]
    if not pending:
        return 0

    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as handle:
        for entry in pending:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")

    return len(pending)


def find_latest_codex_transcript_for_repo(
    *, sessions_root: Path, repo_root: Path
) -> Path | None:
    latest: tuple[float, Path] | None = None
    for transcript_path in sessions_root.rglob("*.jsonl"):
        try:
            with transcript_path.open(encoding="utf-8") as handle:
                first_line = handle.readline().strip()
            if not first_line:
                continue
            first_row = json.loads(first_line)
            if first_row.get("type") != "session_meta":
                continue
            cwd = first_row.get("payload", {}).get("cwd", "")
            if Path(cwd).resolve() != repo_root.resolve():
                continue
            candidate = (transcript_path.stat().st_mtime, transcript_path)
            if latest is None or candidate[0] > latest[0]:
                latest = candidate
        except Exception:
            continue
    return latest[1] if latest else None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--transcript", type=Path, help="Specific Codex transcript to sync")
    parser.add_argument("--log-file", type=Path, default=DEFAULT_LOG_PATH)
    parser.add_argument("--sessions-root", type=Path, default=DEFAULT_SESSIONS_ROOT)
    args = parser.parse_args()

    transcript_path = args.transcript
    if transcript_path is None:
        transcript_path = find_latest_codex_transcript_for_repo(
            sessions_root=args.sessions_root,
            repo_root=REPO_ROOT,
        )

    if transcript_path is None:
        print("No matching Codex transcript found.")
        return 1

    meta = repo_metadata()
    appended = sync_transcript_to_log(
        transcript_path=transcript_path,
        log_path=args.log_file,
        repo=meta["repo"],
        branch=meta["branch"],
        commit=meta["commit"],
        student=meta["student"],
    )
    print(f"Synced {appended} entries from {transcript_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
