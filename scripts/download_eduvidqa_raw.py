#!/usr/bin/env python3
"""
Cache full EduVidQA YouTube transcripts and videos for later dataset derivation.

The script is deliberately sequential and resumable. It writes raw artifacts by
video_id, keeps an archive for yt-dlp, and logs both successes and failures.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import re
import subprocess
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any, NamedTuple
from urllib.parse import parse_qs, urlparse

VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")
VIDEO_COLUMNS = (
    "video_id",
    "youtube_id",
    "yt_id",
    "id",
    "url",
    "video_url",
    "youtube_url",
    "link",
)
URL_COLUMNS = ("url", "video_url", "youtube_url", "link")
TITLE_COLUMNS = ("vid_title", "video_title", "title")
TIMESTAMP_COLUMNS = (
    "timestamp",
    "time",
    "start",
    "start_time",
    "start_sec",
    "answer_start",
    "question_timestamp",
)
TRACE_COLUMNS = ("question_id", "sample_id", "course", "course_id", "split")
DEFAULT_TRANSCRIPT_API_LANGUAGES = ["en", "en-US", "en-GB"]
DEFAULT_YTDLP_SUBTITLE_LANGUAGES = [
    "en",
    "en-orig",
    "en-LUU0EuDKgKo",
    "en-PVQ7OO5RyjI",
]
DEFAULT_TRANSCRIPT_BACKOFF = [30, 120, 300, 900, 1800]
DEFAULT_SUBTITLE_FORMAT = "json3/vtt/best"
YTDLP_SUBTITLE_EXTENSIONS = ("json3", "vtt")
YT_DLP_FORMAT_480P = (
    "bestvideo[height=480]+bestaudio/"
    "best[height=480]/"
    "bestvideo[height<=480]+bestaudio/"
    "best[height<=480]"
)


class VideoRecord(NamedTuple):
    video_id: str
    source: str
    row: dict[str, Any]


class TranscriptResult(NamedTuple):
    status: str
    path: Path
    attempts: int
    error: str | None = None


class VideoDownloadResult(NamedTuple):
    status: str
    return_code: int
    log_path: Path
    error: str | None = None


def extract_video_id(raw: str) -> str | None:
    value = raw.strip()
    if not value:
        return None
    if VIDEO_ID_RE.match(value):
        return value

    parsed = urlparse(value)
    host = parsed.netloc.lower()
    path_parts = [part for part in parsed.path.split("/") if part]

    if "youtube.com" in host:
        query_id = parse_qs(parsed.query).get("v", [None])[0]
        if query_id and VIDEO_ID_RE.match(query_id):
            return query_id
        if path_parts and path_parts[0] in {"embed", "shorts", "live"}:
            candidate = path_parts[1] if len(path_parts) > 1 else ""
            if VIDEO_ID_RE.match(candidate):
                return candidate

    if "youtu.be" in host and path_parts:
        candidate = path_parts[0]
        if VIDEO_ID_RE.match(candidate):
            return candidate

    match = re.search(r"(?<![A-Za-z0-9_-])([A-Za-z0-9_-]{11})(?![A-Za-z0-9_-])", value)
    return match.group(1) if match else None


def _record_from_mapping(row: dict[str, Any], source: str) -> VideoRecord | None:
    for column in VIDEO_COLUMNS:
        value = str(row.get(column) or "").strip()
        video_id = extract_video_id(value)
        if video_id:
            return VideoRecord(video_id=video_id, source=source, row=row)
    for value in row.values():
        if isinstance(value, str):
            video_id = extract_video_id(value)
            if video_id:
                return VideoRecord(video_id=video_id, source=source, row=row)
    return None


def load_video_records(path: Path) -> list[VideoRecord]:
    suffix = path.suffix.lower()
    records: list[VideoRecord] = []
    seen: set[str] = set()

    def add(record: VideoRecord | None) -> None:
        if record is None or record.video_id in seen:
            return
        seen.add(record.video_id)
        records.append(record)

    if suffix == ".jsonl":
        with path.open(encoding="utf-8") as handle:
            for line_no, line in enumerate(handle, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"{path}:{line_no} is not valid JSON") from exc
                if isinstance(row, dict):
                    add(_record_from_mapping(row, f"{path}:{line_no}"))
        return records

    if suffix == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, list):
            rows = payload
        elif isinstance(payload, dict):
            rows = []
            for key in ("videos", "data", "annotations", "items"):
                value = payload.get(key)
                if isinstance(value, list):
                    rows = value
                    break
        else:
            rows = []
        for index, row in enumerate(rows):
            if isinstance(row, dict):
                add(_record_from_mapping(row, f"{path}:{index}"))
        return records

    if suffix == ".csv":
        with path.open(newline="", encoding="utf-8") as handle:
            for line_no, row in enumerate(csv.DictReader(handle), start=2):
                add(_record_from_mapping(dict(row), f"{path}:{line_no}"))
        return records

    with path.open(encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            value = line.strip()
            if not value or value.startswith("#"):
                continue
            video_id = extract_video_id(value)
            if video_id:
                add(
                    VideoRecord(video_id=video_id, source=f"{path}:{line_no}", row={"input": value})
                )
    return records


def load_video_records_many(paths: list[Path]) -> list[VideoRecord]:
    records: list[VideoRecord] = []
    seen: set[str] = set()
    for path in paths:
        for record in load_video_records(path):
            if record.video_id in seen:
                continue
            seen.add(record.video_id)
            records.append(record)
    return records


def ensure_output_dirs(output_root: Path) -> None:
    for dirname in ("transcripts", "transcripts_raw", "videos", "logs", "archive"):
        (output_root / dirname).mkdir(parents=True, exist_ok=True)


def sleep_random(min_seconds: float, max_seconds: float) -> None:
    if max_seconds <= 0:
        return
    if min_seconds > max_seconds:
        min_seconds, max_seconds = max_seconds, min_seconds
    time.sleep(random.uniform(min_seconds, max_seconds))


def _transcript_to_raw_data(transcript: Any) -> list[dict[str, Any]]:
    if hasattr(transcript, "to_raw_data"):
        return list(transcript.to_raw_data())
    rows: list[dict[str, Any]] = []
    for item in transcript:
        if isinstance(item, dict):
            rows.append(item)
            continue
        rows.append(
            {
                "text": getattr(item, "text", ""),
                "start": getattr(item, "start", None),
                "duration": getattr(item, "duration", None),
            }
        )
    return rows


def default_transcript_fetcher(video_id: str, languages: list[str]) -> list[dict[str, Any]]:
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
    except ImportError as exc:
        raise RuntimeError(
            "Missing dependency: install youtube-transcript-api before fetching transcripts"
        ) from exc

    api = YouTubeTranscriptApi()
    if hasattr(api, "fetch"):
        return _transcript_to_raw_data(api.fetch(video_id, languages=languages))
    return _transcript_to_raw_data(
        YouTubeTranscriptApi.get_transcript(video_id, languages=languages)
    )


def normalize_ytdlp_json3(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for event in payload.get("events", []):
        if not isinstance(event, dict):
            continue
        pieces = []
        for segment in event.get("segs", []) or []:
            if isinstance(segment, dict):
                pieces.append(str(segment.get("utf8") or ""))
        text = "".join(pieces).replace("\n", " ").strip()
        if not text:
            continue
        start_ms = event.get("tStartMs")
        duration_ms = event.get("dDurationMs")
        rows.append(
            {
                "text": text,
                "start": None if start_ms is None else float(start_ms) / 1000.0,
                "duration": None if duration_ms is None else float(duration_ms) / 1000.0,
            }
        )
    return rows


def _parse_vtt_timestamp(raw: str) -> float:
    value = raw.strip().replace(",", ".")
    parts = value.split(":")
    if len(parts) == 2:
        minutes, seconds = parts
        return int(minutes) * 60 + float(seconds)
    if len(parts) == 3:
        hours, minutes, seconds = parts
        return int(hours) * 3600 + int(minutes) * 60 + float(seconds)
    raise ValueError(f"Invalid VTT timestamp: {raw}")


def normalize_vtt(text: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    lines = text.splitlines()
    index = 0
    tag_re = re.compile(r"<[^>]+>")
    while index < len(lines):
        line = lines[index].strip()
        index += 1
        if "-->" not in line:
            continue
        start_raw, end_raw = [part.strip().split(" ")[0] for part in line.split("-->", 1)]
        try:
            start = _parse_vtt_timestamp(start_raw)
            end = _parse_vtt_timestamp(end_raw)
        except ValueError:
            continue
        payload_lines: list[str] = []
        while index < len(lines) and lines[index].strip():
            payload_lines.append(tag_re.sub("", lines[index].strip()))
            index += 1
        segment_text = " ".join(payload_lines).strip()
        if segment_text:
            rows.append(
                {
                    "text": segment_text,
                    "start": start,
                    "duration": max(0.0, end - start),
                }
            )
    return rows


def normalize_subtitle_file(path: Path) -> list[dict[str, Any]]:
    if path.suffix == ".json3":
        return normalize_ytdlp_json3(json.loads(path.read_text(encoding="utf-8")))
    if path.suffix == ".vtt":
        return normalize_vtt(path.read_text(encoding="utf-8"))
    raise ValueError(f"Unsupported subtitle format: {path.suffix}")


def is_valid_normalized_transcript(path: Path) -> bool:
    if not path.exists():
        return False
    try:
        rows = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return False
    if not isinstance(rows, list) or not rows:
        return False
    for row in rows:
        if not isinstance(row, dict):
            return False
        if not str(row.get("text") or "").strip():
            return False
        if "start" not in row or "duration" not in row:
            return False
    return True


def write_json_atomic(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temp_path.replace(path)


def transcript_archive_path(output_root: Path) -> Path:
    return output_root / "archive" / "transcript_archive.txt"


def add_to_transcript_archive(output_root: Path, video_id: str) -> None:
    path = transcript_archive_path(output_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    line = f"youtube {video_id}"
    existing: set[str] = set()
    if path.exists():
        existing = {item.strip() for item in path.read_text(encoding="utf-8").splitlines()}
    if line not in existing:
        with path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")


def _subtitle_language_priority(path: Path, video_id: str) -> tuple[int, int, str]:
    name = path.name
    ext_priority = 0 if path.suffix == ".json3" else 1
    language = name.removeprefix(f"{video_id}.").removesuffix(path.suffix).rstrip(".")
    preferred = {
        "en-orig": 1,
        "en": 2,
        "en-US": 2,
        "en-GB": 3,
    }
    language_priority = preferred.get(language, 10)
    if language.startswith("en-") and not language.startswith("en-en-") and language != "en-orig":
        language_priority = min(language_priority, 0)
    if language.startswith("en-en-"):
        language_priority = min(language_priority, 4)
    return (language_priority, ext_priority, name)


def find_downloaded_subtitle(raw_dir: Path, video_id: str) -> Path | None:
    candidates: list[Path] = []
    for extension in YTDLP_SUBTITLE_EXTENSIONS:
        candidates.extend(raw_dir.glob(f"{video_id}*.{extension}"))
    if not candidates:
        return None
    return sorted(candidates, key=lambda path: _subtitle_language_priority(path, video_id))[0]


def build_ytdlp_transcript_command(
    *,
    video_id: str,
    output_root: Path,
    languages: list[str],
    subtitle_format: str,
    sleep_requests: int,
    sleep_subtitles: int,
    retries: int,
    cookies_from_browser: str | None = None,
    cookies_file: Path | None = None,
    remote_components: str | None = None,
) -> list[str]:
    output_root = output_root.resolve()
    command = [
        sys.executable,
        "-m",
        "yt_dlp",
        "--no-playlist",
        "--skip-download",
        "--write-subs",
        "--write-auto-subs",
        "--sub-langs",
        ",".join(languages),
        "--sub-format",
        subtitle_format,
        "--newline",
        "--sleep-requests",
        str(sleep_requests),
        "--sleep-subtitles",
        str(sleep_subtitles),
        "--retries",
        str(retries),
        "--socket-timeout",
        "30",
        "-o",
        str(output_root / "transcripts_raw" / "%(id)s.%(ext)s"),
        f"https://www.youtube.com/watch?v={video_id}",
    ]
    if cookies_from_browser:
        command[-1:-1] = ["--cookies-from-browser", cookies_from_browser]
    if cookies_file:
        command[-1:-1] = ["--cookies", str(cookies_file)]
    if remote_components:
        command[-1:-1] = ["--remote-components", remote_components]
    return command


def classify_transcript_error(error: Exception) -> str:
    name = error.__class__.__name__
    if name in {"IpBlocked", "RequestBlocked"}:
        return "blocked"
    if name in {
        "TranscriptsDisabled",
        "NoTranscriptFound",
        "VideoUnavailable",
        "VideoUnplayable",
        "InvalidVideoId",
        "AgeRestricted",
    }:
        return "unavailable"
    return "failed"


def fetch_transcript_with_cache(
    *,
    video_id: str,
    transcript_dir: Path,
    languages: list[str],
    fetcher: Callable[[str, list[str]], list[dict[str, Any]]] = default_transcript_fetcher,
    min_sleep: float = 5,
    max_sleep: float = 15,
    backoff_seconds: list[int] | None = None,
) -> TranscriptResult:
    transcript_dir.mkdir(parents=True, exist_ok=True)
    out_path = transcript_dir / f"{video_id}.json"
    if out_path.exists():
        return TranscriptResult(status="cached", path=out_path, attempts=0)

    waits = backoff_seconds if backoff_seconds is not None else DEFAULT_TRANSCRIPT_BACKOFF
    attempts = max(1, len(waits) + 1)
    last_error: Exception | None = None

    for attempt in range(attempts):
        sleep_random(min_sleep, max_sleep)
        try:
            data = fetcher(video_id, languages)
            out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            return TranscriptResult(status="downloaded", path=out_path, attempts=attempt + 1)
        except Exception as exc:
            last_error = exc
            status = classify_transcript_error(exc)
            if status in {"blocked", "unavailable"}:
                return TranscriptResult(
                    status=status,
                    path=out_path,
                    attempts=attempt + 1,
                    error=str(exc),
                )
            if attempt < len(waits):
                time.sleep(waits[attempt])

    return TranscriptResult(
        status="failed",
        path=out_path,
        attempts=attempts,
        error=str(last_error) if last_error else "unknown error",
    )


def download_transcript_with_ytdlp_cache(
    *,
    video_id: str,
    output_root: Path,
    languages: list[str],
    subtitle_format: str,
    min_sleep: float,
    max_sleep: float,
    sleep_requests: int,
    sleep_subtitles: int,
    retries: int,
    dry_run: bool,
    force: bool,
    cookies_from_browser: str | None,
    cookies_file: Path | None,
    remote_components: str | None,
    runner: Callable[..., subprocess.CompletedProcess[str]] | None = None,
) -> TranscriptResult:
    transcript_dir = output_root / "transcripts"
    raw_dir = output_root / "transcripts_raw"
    transcript_dir.mkdir(parents=True, exist_ok=True)
    raw_dir.mkdir(parents=True, exist_ok=True)

    out_path = transcript_dir / f"{video_id}.json"
    if is_valid_normalized_transcript(out_path) and not force:
        add_to_transcript_archive(output_root, video_id)
        return TranscriptResult(status="cached", path=out_path, attempts=0)

    if not force:
        raw_path = find_downloaded_subtitle(raw_dir, video_id)
        if raw_path is not None:
            try:
                rows = normalize_subtitle_file(raw_path)
            except Exception:
                rows = []
            if rows:
                write_json_atomic(out_path, rows)
                add_to_transcript_archive(output_root, video_id)
                return TranscriptResult(status="normalized", path=out_path, attempts=0)

    sleep_random(min_sleep, max_sleep)

    command = build_ytdlp_transcript_command(
        video_id=video_id,
        output_root=output_root,
        languages=languages,
        subtitle_format=subtitle_format,
        sleep_requests=sleep_requests,
        sleep_subtitles=sleep_subtitles,
        retries=retries,
        cookies_from_browser=cookies_from_browser,
        cookies_file=cookies_file,
        remote_components=remote_components,
    )
    log_path = output_root / "logs" / f"{video_id}_yt_dlp_transcript.log"
    if dry_run:
        print(" ".join(command))
        write_ytdlp_log(log_path=log_path, command=command, stdout="dry run; command not executed")
        return TranscriptResult(status="dry_run", path=out_path, attempts=0)

    for extension in YTDLP_SUBTITLE_EXTENSIONS:
        for stale_path in raw_dir.glob(f"{video_id}*.{extension}"):
            if force:
                stale_path.unlink()

    if runner is None:
        try:
            with log_path.open("w", encoding="utf-8") as log_handle:
                log_handle.write("COMMAND:\n")
                log_handle.write(" ".join(command))
                log_handle.write("\n\nOUTPUT:\n")
                log_handle.flush()
                process = subprocess.Popen(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                )
                assert process.stdout is not None
                for line in process.stdout:
                    print(line, end="")
                    log_handle.write(line)
                    log_handle.flush()
                return_code = process.wait()
        except FileNotFoundError:
            message = "yt-dlp not found. Install with: pip install yt-dlp"
            print(message)
            write_ytdlp_log(log_path=log_path, command=command, error=message)
            return TranscriptResult(status="failed", path=out_path, attempts=1, error=message)
    else:
        try:
            completed = runner(command, text=True, capture_output=True)
        except FileNotFoundError:
            message = "yt-dlp not found. Install with: pip install yt-dlp"
            print(message)
            write_ytdlp_log(log_path=log_path, command=command, error=message)
            return TranscriptResult(status="failed", path=out_path, attempts=1, error=message)
        return_code = completed.returncode
        write_ytdlp_log(
            log_path=log_path,
            command=command,
            stdout=completed.stdout or "",
            stderr=completed.stderr or "",
        )

    if return_code != 0:
        log_text = log_path.read_text(encoding="utf-8") if log_path.exists() else ""
        if "HTTP Error 429" in log_text or "Too Many Requests" in log_text:
            return TranscriptResult(
                status="blocked",
                path=out_path,
                attempts=1,
                error=f"yt-dlp hit HTTP 429 Too Many Requests; see {log_path}",
            )
        return TranscriptResult(
            status="failed",
            path=out_path,
            attempts=1,
            error=f"yt-dlp exited with code {return_code}; see {log_path}",
        )

    raw_path = find_downloaded_subtitle(raw_dir, video_id)
    if raw_path is None:
        return TranscriptResult(
            status="unavailable",
            path=out_path,
            attempts=1,
            error=f"No subtitle file produced; see {log_path}",
        )

    try:
        rows = normalize_subtitle_file(raw_path)
    except Exception as exc:
        return TranscriptResult(
            status="failed",
            path=out_path,
            attempts=1,
            error=f"Could not normalize {raw_path}: {exc}",
        )
    if not rows:
        return TranscriptResult(
            status="unavailable",
            path=out_path,
            attempts=1,
            error=f"Subtitle file was empty after normalization: {raw_path}",
        )
    write_json_atomic(out_path, rows)
    add_to_transcript_archive(output_root, video_id)
    return TranscriptResult(status="downloaded", path=out_path, attempts=1)


def build_ytdlp_command(
    *,
    video_id: str,
    output_root: Path,
    min_sleep: int,
    max_sleep: int,
    sleep_requests: int,
    limit_rate: str,
    retries: int,
    cookies_from_browser: str | None = None,
    cookies_file: Path | None = None,
    remote_components: str | None = None,
) -> list[str]:
    output_root = output_root.resolve()
    command = [
        sys.executable,
        "-m",
        "yt_dlp",
        "--no-playlist",
        "--continue",
        "--format",
        YT_DLP_FORMAT_480P,
        "--merge-output-format",
        "mp4",
        "--write-info-json",
        "--newline",
        "--download-archive",
        str(output_root / "archive" / "video_archive.txt"),
        "--sleep-requests",
        str(sleep_requests),
        "--sleep-interval",
        str(min_sleep),
        "--max-sleep-interval",
        str(max_sleep),
        "--limit-rate",
        limit_rate,
        "--retries",
        str(retries),
        "--fragment-retries",
        str(retries),
        "--socket-timeout",
        "30",
        "-o",
        str(output_root / "videos" / "%(id)s.%(ext)s"),
        f"https://www.youtube.com/watch?v={video_id}",
    ]
    if cookies_from_browser:
        command[-1:-1] = ["--cookies-from-browser", cookies_from_browser]
    if cookies_file:
        command[-1:-1] = ["--cookies", str(cookies_file)]
    if remote_components:
        command[-1:-1] = ["--remote-components", remote_components]
    return command


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def _first_non_empty(row: dict[str, Any], columns: tuple[str, ...]) -> Any:
    for column in columns:
        value = row.get(column)
        if value not in (None, ""):
            return value
    return None


def build_artifact_payload(
    *,
    kind: str,
    record: VideoRecord,
    status: str,
    **extra: Any,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "kind": kind,
        "video_id": record.video_id,
        "status": status,
        "source": record.source,
    }

    url = _first_non_empty(record.row, URL_COLUMNS)
    title = _first_non_empty(record.row, TITLE_COLUMNS)
    timestamp = _first_non_empty(record.row, TIMESTAMP_COLUMNS)
    if url is not None:
        payload["url"] = url
    if title is not None:
        payload["title"] = title
    if timestamp is not None:
        payload["timestamp"] = timestamp
    for column in TRACE_COLUMNS:
        value = record.row.get(column)
        if value not in (None, ""):
            payload[column] = value

    payload.update({key: value for key, value in extra.items() if value is not None})
    return payload


def write_ytdlp_log(
    *,
    log_path: Path,
    command: list[str],
    stdout: str = "",
    stderr: str = "",
    error: str | None = None,
) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    sections = [
        "COMMAND:",
        " ".join(command),
        "",
        "STDOUT:",
        stdout or "",
        "",
        "STDERR:",
        stderr or "",
    ]
    if error:
        sections.extend(["", "ERROR:", error])
    log_path.write_text("\n".join(sections), encoding="utf-8")


def download_video(
    *,
    video_id: str,
    output_root: Path,
    min_sleep: int,
    max_sleep: int,
    sleep_requests: int,
    limit_rate: str,
    retries: int,
    dry_run: bool,
    cookies_from_browser: str | None,
    cookies_file: Path | None,
    remote_components: str | None,
    runner: Callable[..., subprocess.CompletedProcess[str]] | None = None,
) -> VideoDownloadResult:
    command = build_ytdlp_command(
        video_id=video_id,
        output_root=output_root,
        min_sleep=min_sleep,
        max_sleep=max_sleep,
        sleep_requests=sleep_requests,
        limit_rate=limit_rate,
        retries=retries,
        cookies_from_browser=cookies_from_browser,
        cookies_file=cookies_file,
        remote_components=remote_components,
    )
    log_path = output_root / "logs" / f"{video_id}_yt_dlp.log"
    if dry_run:
        print(" ".join(command))
        write_ytdlp_log(log_path=log_path, command=command, stdout="dry run; command not executed")
        return VideoDownloadResult(status="dry_run", return_code=0, log_path=log_path)
    if runner is None:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with log_path.open("w", encoding="utf-8") as log_handle:
                log_handle.write("COMMAND:\n")
                log_handle.write(" ".join(command))
                log_handle.write("\n\nOUTPUT:\n")
                log_handle.flush()
                process = subprocess.Popen(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                )
                assert process.stdout is not None
                for line in process.stdout:
                    print(line, end="")
                    log_handle.write(line)
                    log_handle.flush()
                return_code = process.wait()
        except FileNotFoundError:
            message = "yt-dlp not found. Install with: pip install yt-dlp"
            print(message)
            write_ytdlp_log(log_path=log_path, command=command, error=message)
            return VideoDownloadResult(
                status="failed",
                return_code=127,
                log_path=log_path,
                error=message,
            )
        return VideoDownloadResult(
            status="downloaded" if return_code == 0 else "failed",
            return_code=return_code,
            log_path=log_path,
        )
    try:
        completed = runner(command, text=True, capture_output=True)
    except FileNotFoundError:
        message = "yt-dlp not found. Install with: pip install yt-dlp"
        print(message)
        write_ytdlp_log(log_path=log_path, command=command, error=message)
        return VideoDownloadResult(
            status="failed",
            return_code=127,
            log_path=log_path,
            error=message,
        )

    stdout = completed.stdout or ""
    stderr = completed.stderr or ""
    write_ytdlp_log(log_path=log_path, command=command, stdout=stdout, stderr=stderr)
    return VideoDownloadResult(
        status="downloaded" if completed.returncode == 0 else "failed",
        return_code=completed.returncode,
        log_path=log_path,
        error=(stderr.strip() or None) if completed.returncode != 0 else None,
    )


def parse_int_list(raw: str) -> list[int]:
    if not raw.strip():
        return []
    return [int(part.strip()) for part in raw.split(",") if part.strip()]


def parse_languages(raw: str | None, default: list[str]) -> list[str]:
    if raw is None:
        return default
    values = [part.strip() for part in raw.split(",") if part.strip()]
    return values or default


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Sequentially cache EduVidQA full transcripts and full YouTube videos.",
    )
    parser.add_argument(
        "--input",
        required=True,
        type=Path,
        nargs="+",
        help="One or more TXT/JSONL/JSON/CSV video manifests. Video IDs are deduplicated globally.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("data/eduvidqa/raw"),
        help="Raw cache root directory",
    )
    parser.add_argument(
        "--mode",
        choices=("both", "transcripts", "videos"),
        default="both",
        help="Which artifacts to download",
    )
    parser.add_argument(
        "--transcript-provider",
        choices=("yt-dlp", "youtube-transcript-api"),
        default="yt-dlp",
        help="Transcript backend. yt-dlp is recommended for YouTube captions with cookies/EJS.",
    )
    parser.add_argument(
        "--languages",
        help=(
            "Comma-separated transcript languages. Defaults to English fallbacks for the selected "
            "transcript provider."
        ),
    )
    parser.add_argument(
        "--subtitle-format",
        default=DEFAULT_SUBTITLE_FORMAT,
        help="yt-dlp subtitle format preference for transcript mode",
    )
    parser.add_argument(
        "--sleep-subtitles",
        type=int,
        default=2,
        help="yt-dlp sleep before each subtitle download",
    )
    parser.add_argument(
        "--force-transcripts",
        action="store_true",
        help="Re-download transcripts even if transcripts/{video_id}.json already exists",
    )
    parser.add_argument("--transcript-min-sleep", type=float, default=5)
    parser.add_argument("--transcript-max-sleep", type=float, default=15)
    parser.add_argument(
        "--transcript-backoff",
        default=",".join(str(value) for value in DEFAULT_TRANSCRIPT_BACKOFF),
        help="Comma-separated retry waits in seconds",
    )
    parser.add_argument("--video-min-sleep", type=int, default=60)
    parser.add_argument("--video-max-sleep", type=int, default=180)
    parser.add_argument("--sleep-requests", type=int, default=2)
    parser.add_argument("--limit-rate", default="3M")
    parser.add_argument("--retries", type=int, default=5)
    parser.add_argument(
        "--cookies-from-browser",
        help="Pass yt-dlp cookies from a logged-in browser, e.g. firefox, chrome, chromium.",
    )
    parser.add_argument(
        "--cookies",
        type=Path,
        help="Path to a Netscape-format cookies.txt file for yt-dlp.",
    )
    parser.add_argument(
        "--remote-components",
        help="Pass yt-dlp remote component source, e.g. ejs:npm or ejs:github.",
    )
    parser.add_argument(
        "--continue-on-block",
        action="store_true",
        help="Continue transcript loop after RequestBlocked/IpBlocked instead of stopping early",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print yt-dlp commands and skip network work for videos",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    output_root = args.output_root.resolve()
    ensure_output_dirs(output_root)

    records = load_video_records_many(args.input)
    if not records:
        parser.error(f"No video IDs found in: {', '.join(str(path) for path in args.input)}")

    manifest_log = output_root / "logs" / "manifest.jsonl"
    error_log = output_root / "logs" / "errors.jsonl"
    if args.transcript_provider == "yt-dlp":
        default_languages = DEFAULT_YTDLP_SUBTITLE_LANGUAGES
    else:
        default_languages = DEFAULT_TRANSCRIPT_API_LANGUAGES
    languages = parse_languages(args.languages, default_languages)
    transcript_backoff = parse_int_list(args.transcript_backoff)

    for index, record in enumerate(records, start=1):
        print(f"[{index}/{len(records)}] {record.video_id}")

        if args.mode in {"both", "transcripts"}:
            if args.transcript_provider == "yt-dlp":
                result = download_transcript_with_ytdlp_cache(
                    video_id=record.video_id,
                    output_root=output_root,
                    languages=languages,
                    subtitle_format=args.subtitle_format,
                    min_sleep=args.transcript_min_sleep,
                    max_sleep=args.transcript_max_sleep,
                    sleep_requests=args.sleep_requests,
                    sleep_subtitles=args.sleep_subtitles,
                    retries=args.retries,
                    dry_run=args.dry_run,
                    force=args.force_transcripts,
                    cookies_from_browser=args.cookies_from_browser,
                    cookies_file=args.cookies,
                    remote_components=args.remote_components,
                )
            else:
                result = fetch_transcript_with_cache(
                    video_id=record.video_id,
                    transcript_dir=output_root / "transcripts",
                    languages=languages,
                    min_sleep=args.transcript_min_sleep,
                    max_sleep=args.transcript_max_sleep,
                    backoff_seconds=transcript_backoff,
                )
            payload = build_artifact_payload(
                kind="transcript",
                record=record,
                status=result.status,
                path=str(result.path),
                attempts=result.attempts,
                provider=args.transcript_provider,
            )
            if result.error:
                payload["error"] = result.error
                append_jsonl(error_log, payload)
            else:
                append_jsonl(manifest_log, payload)
            if result.status == "blocked" and not args.continue_on_block:
                print(
                    "Transcript fetch blocked; stopping early. Use --continue-on-block to override."
                )
                return 2

        if args.mode in {"both", "videos"}:
            video_result = download_video(
                video_id=record.video_id,
                output_root=output_root,
                min_sleep=args.video_min_sleep,
                max_sleep=args.video_max_sleep,
                sleep_requests=args.sleep_requests,
                limit_rate=args.limit_rate,
                retries=args.retries,
                dry_run=args.dry_run,
                cookies_from_browser=args.cookies_from_browser,
                cookies_file=args.cookies,
                remote_components=args.remote_components,
            )
            payload = build_artifact_payload(
                kind="video",
                record=record,
                status=video_result.status,
                return_code=video_result.return_code,
                log_path=str(video_result.log_path),
                error=video_result.error,
            )
            append_jsonl(manifest_log if video_result.return_code == 0 else error_log, payload)

    return 0


if __name__ == "__main__":
    sys.exit(main())
