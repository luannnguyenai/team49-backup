"""Cut P3b video clips from lecture videos using P3b input unit boundaries."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

_TIMESTAMP_LINE_PATTERN = re.compile(r"^(\d{2}):(\d{2}):(\d{2})$")
_YOUTUBE_ID_PATTERN = re.compile(r"(?:v=|youtu\.be/)([A-Za-z0-9_-]{6,})")


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _dump_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _slugify_filename(raw: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", raw.casefold()).strip("-")


def _extract_youtube_id(raw_url: str | None) -> str | None:
    if not isinstance(raw_url, str):
        return None
    match = _YOUTUBE_ID_PATTERN.search(raw_url)
    return match.group(1) if match else None


def _build_video_index(course_dir: Path) -> dict[str, Path]:
    transcript_dir = course_dir / "transcripts"
    video_dir = course_dir / "videos"
    index: dict[str, Path] = {}
    for transcript_path in sorted(transcript_dir.glob("*_transcript.txt")):
        video_id: str | None = None
        for line in transcript_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("Video ID:"):
                video_id = line.partition(":")[2].strip() or None
                break
            if line.startswith("URL:"):
                video_id = _extract_youtube_id(line.partition(":")[2].strip())
        if not video_id:
            continue
        stem = transcript_path.name.removesuffix("_transcript.txt")
        for suffix in (".mp4", ".mkv", ".webm", ".mov"):
            candidate = video_dir / f"{stem}{suffix}"
            if candidate.exists():
                index[video_id] = candidate
                break
    return index


def _run_ffmpeg_cut(
    *,
    source_video: Path,
    output_path: Path,
    start_s: int,
    end_s: int,
    overwrite: bool,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists() and not overwrite:
        return

    duration_s = max(1, end_s - start_s)
    command = [
        "ffmpeg",
        "-y" if overwrite else "-n",
        "-hide_banner",
        "-loglevel",
        "error",
        "-ss",
        str(start_s),
        "-i",
        str(source_video),
        "-t",
        str(duration_s),
        "-map",
        "0:v:0?",
        "-map",
        "0:a:0?",
        "-c",
        "copy",
        "-avoid_negative_ts",
        "make_zero",
        str(output_path),
    ]
    subprocess.run(command, check=True)


def cut_segments(
    *,
    course_dir: Path,
    p3b_input_dir: Path,
    output_clip_dir: Path,
    manifest_dir: Path,
    overwrite: bool,
) -> dict[str, Any]:
    video_index = _build_video_index(course_dir)
    if not video_index:
        raise RuntimeError(f"No local videos found from transcripts under {course_dir}")

    course_id = course_dir.name
    total_clips = 0
    total_duration_s = 0
    manifests: list[str] = []
    missing_videos: list[dict[str, str | None]] = []

    for input_path in sorted(p3b_input_dir.glob("*.json")):
        payload = _load_json(input_path)
        lecture_context = payload.get("lecture_context") or {}
        lecture_id = lecture_context.get("lecture_id")
        youtube_url = lecture_context.get("youtube_url")
        video_id = _extract_youtube_id(youtube_url)
        source_video = video_index.get(video_id or "")
        if source_video is None:
            missing_videos.append(
                {
                    "p3b_input": str(input_path),
                    "lecture_id": lecture_id,
                    "youtube_url": youtube_url,
                    "video_id": video_id,
                }
            )
            continue

        buffer_s = int(payload.get("buffer_s") or 0)
        lecture_clip_dir = output_clip_dir / str(lecture_id)
        clips: list[dict[str, Any]] = []
        for unit in payload.get("units") or []:
            if not isinstance(unit, dict):
                continue
            unit_id = unit.get("unit_id")
            content_ref = unit.get("content_ref") or {}
            start_s = int(content_ref.get("start_s") or 0)
            end_s = int(content_ref.get("end_s") or 0)
            if not isinstance(unit_id, str) or end_s <= start_s:
                continue

            buffered_start_s = max(0, start_s - buffer_s)
            buffered_end_s = end_s + buffer_s
            clip_filename = f"{_slugify_filename(unit_id).replace('local-', 'local--')}.mp4"
            clip_path = lecture_clip_dir / clip_filename
            _run_ffmpeg_cut(
                source_video=source_video,
                output_path=clip_path,
                start_s=buffered_start_s,
                end_s=buffered_end_s,
                overwrite=overwrite,
            )
            duration_s = buffered_end_s - buffered_start_s
            total_clips += 1
            total_duration_s += duration_s
            clips.append(
                {
                    "unit_id": unit_id,
                    "unit_name": unit.get("name"),
                    "source_video_path": str(source_video),
                    "clip_path": str(clip_path),
                    "video_clip_ref": {
                        "local_path": str(clip_path),
                        "source_video_path": str(source_video),
                        "start_s": start_s,
                        "end_s": end_s,
                        "buffer_s": buffer_s,
                        "buffered_start_s": buffered_start_s,
                        "buffered_end_s": buffered_end_s,
                        "duration_s": duration_s,
                        "cut_method": "ffmpeg_stream_copy",
                    },
                }
            )

        manifest = {
            "output_filename": f"p3b__{course_id}__{lecture_id}.json",
            "run_id": f"p3b_{course_id.casefold()}_{lecture_id}",
            "stage_id": "p3b",
            "course_id": course_id,
            "lecture_id": lecture_id,
            "lecture_context": lecture_context,
            "source_trace": payload.get("source_trace"),
            "buffer_s": buffer_s,
            "source_video_path": str(source_video),
            "clips": clips,
        }
        manifest_path = manifest_dir / f"{input_path.stem.removesuffix('_p1')}.json"
        _dump_json(manifest_path, manifest)
        manifests.append(str(manifest_path))

    if missing_videos:
        raise RuntimeError(
            f"Missing source videos for {len(missing_videos)} lectures: {missing_videos}"
        )

    return {
        "course_id": course_id,
        "clips": total_clips,
        "duration_hours": round(total_duration_s / 3600, 2),
        "manifest_files": len(manifests),
        "clip_dir": str(output_clip_dir),
        "manifest_dir": str(manifest_dir),
    }


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Cut P3b video segment clips from local lecture videos."
    )
    parser.add_argument("--course-dir", required=True)
    parser.add_argument("--p3b-input-dir", required=True)
    parser.add_argument("--output-clip-dir", required=True)
    parser.add_argument("--manifest-dir", required=True)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    report = cut_segments(
        course_dir=Path(args.course_dir),
        p3b_input_dir=Path(args.p3b_input_dir),
        output_clip_dir=Path(args.output_clip_dir),
        manifest_dir=Path(args.manifest_dir),
        overwrite=args.overwrite,
    )
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
