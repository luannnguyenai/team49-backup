"""Build the lightweight asset manifest used by production backend images."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

_LECTURE_NUMBER_RE = re.compile(r"(?:lecture|Lecture)[_ -]?0*(\d+)")
_KIND_TO_DIR = {
    "videos": "videos",
    "slides": "slides",
    "transcripts": "transcripts",
}


def _extract_lecture_number(filename: str) -> int | None:
    match = _LECTURE_NUMBER_RE.search(filename)
    if match is None:
        return None
    return int(match.group(1))


def build_asset_manifest(courses_dir: Path) -> dict[str, dict[str, dict[str, str]]]:
    manifest: dict[str, dict[str, dict[str, str]]] = {
        "videos": {},
        "slides": {},
        "transcripts": {},
    }

    if not courses_dir.exists():
        return manifest

    for course_dir in sorted(path for path in courses_dir.iterdir() if path.is_dir()):
        course_slug = course_dir.name.lower()

        for kind, subdir_name in _KIND_TO_DIR.items():
            asset_dir = course_dir / subdir_name
            if not asset_dir.exists():
                continue

            lecture_map: dict[str, str] = {}
            for asset_path in sorted(path for path in asset_dir.iterdir() if path.is_file()):
                lecture_num = _extract_lecture_number(asset_path.name)
                if lecture_num is None:
                    continue
                lecture_map[str(lecture_num)] = asset_path.name

            if lecture_map:
                manifest[kind][course_slug] = lecture_map

    return manifest


def materialize_asset_manifest(
    *,
    courses_dir: Path,
    output_path: Path,
    preserve_existing: bool = False,
) -> bool:
    manifest = build_asset_manifest(courses_dir)
    has_assets = any(manifest[kind] for kind in manifest)

    if not has_assets and preserve_existing and output_path.exists():
        return False

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--courses-dir", type=Path, default=Path("data/courses"))
    parser.add_argument("--output", type=Path, default=Path("data/asset_manifest.json"))
    parser.add_argument(
        "--preserve-existing",
        action="store_true",
        help="Keep the current output file when the source asset tree is unavailable.",
    )
    args = parser.parse_args()

    changed = materialize_asset_manifest(
        courses_dir=args.courses_dir,
        output_path=args.output,
        preserve_existing=args.preserve_existing,
    )
    print(
        json.dumps(
            {
                "courses_dir": str(args.courses_dir),
                "output": str(args.output),
                "updated": changed,
            },
            ensure_ascii=False,
        ),
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
