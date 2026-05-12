"""Download a versioned canonical bundle from S3 into a local directory."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path, PurePosixPath


def parse_s3_uri(s3_uri: str) -> tuple[str, str]:
    if not s3_uri.startswith("s3://"):
        raise ValueError(f"Expected s3:// URI, got: {s3_uri!r}")

    remainder = s3_uri[5:]
    bucket, _, key = remainder.partition("/")
    if not bucket or not key:
        raise ValueError(f"S3 URI must include bucket and prefix: {s3_uri!r}")

    normalized_key = key.strip("/")
    if not normalized_key:
        raise ValueError(f"S3 URI prefix is empty: {s3_uri!r}")

    return bucket, normalized_key


def relative_key_path(prefix: str, key: str) -> Path:
    prefix_path = PurePosixPath(prefix)
    key_path = PurePosixPath(key)
    if key_path == prefix_path:
        raise ValueError(f"S3 object key resolves to the bundle root itself: {key!r}")
    return Path(*key_path.relative_to(prefix_path).parts)


def download_bundle(*, s3_uri: str, output_dir: Path) -> dict[str, object]:
    import boto3

    bucket, prefix = parse_s3_uri(s3_uri)
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    s3_client = boto3.client("s3")
    paginator = s3_client.get_paginator("list_objects_v2")

    downloaded_files = 0
    downloaded_bytes = 0

    for page in paginator.paginate(Bucket=bucket, Prefix=f"{prefix}/"):
        for item in page.get("Contents", []):
            key = str(item["Key"])
            if key.endswith("/"):
                continue

            destination = output_dir / relative_key_path(prefix, key)
            destination.parent.mkdir(parents=True, exist_ok=True)
            s3_client.download_file(bucket, key, str(destination))

            downloaded_files += 1
            downloaded_bytes += int(item.get("Size", 0))

    if downloaded_files == 0:
        raise FileNotFoundError(f"No bundle files found at {s3_uri}")

    manifest_path = output_dir / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(
            f"Bundle download from {s3_uri} completed without manifest.json in {output_dir}"
        )

    return {
        "s3_uri": s3_uri,
        "output_dir": str(output_dir),
        "downloaded_files": downloaded_files,
        "downloaded_bytes": downloaded_bytes,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--s3-uri", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    report = download_bundle(s3_uri=args.s3_uri, output_dir=args.output_dir)
    print(report, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
