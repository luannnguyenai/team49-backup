import csv
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


def _load_downloader_module():
    module_path = Path(__file__).resolve().parent.parent / "scripts" / "download_eduvidqa_raw.py"
    spec = importlib.util.spec_from_file_location("download_eduvidqa_raw", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class EduVidQADownloaderTests(unittest.TestCase):
    def test_extract_video_id_from_common_youtube_inputs(self):
        module = _load_downloader_module()

        self.assertEqual(module.extract_video_id("dQw4w9WgXcQ"), "dQw4w9WgXcQ")
        self.assertEqual(
            module.extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=12"),
            "dQw4w9WgXcQ",
        )
        self.assertEqual(
            module.extract_video_id("https://youtu.be/dQw4w9WgXcQ?si=test"),
            "dQw4w9WgXcQ",
        )
        self.assertEqual(
            module.extract_video_id("https://www.youtube.com/embed/dQw4w9WgXcQ"),
            "dQw4w9WgXcQ",
        )

    def test_load_video_records_from_text_jsonl_and_csv(self):
        module = _load_downloader_module()

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            text_path = root / "videos.txt"
            text_path.write_text(
                "\n".join(
                    [
                        "# comment",
                        "https://youtu.be/dQw4w9WgXcQ",
                        "abcdefghijk",
                    ]
                ),
                encoding="utf-8",
            )

            jsonl_path = root / "videos.jsonl"
            jsonl_path.write_text(
                json.dumps({"youtube_url": "https://www.youtube.com/watch?v=zzzzzzzzzzz"})
                + "\n",
                encoding="utf-8",
            )

            csv_path = root / "videos.csv"
            with csv_path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=["video_id", "title"])
                writer.writeheader()
                writer.writerow({"video_id": "yyyyyyyyyyy", "title": "Lecture"})

            self.assertEqual(
                [record.video_id for record in module.load_video_records(text_path)],
                ["dQw4w9WgXcQ", "abcdefghijk"],
            )
            self.assertEqual(
                [record.video_id for record in module.load_video_records(jsonl_path)],
                ["zzzzzzzzzzz"],
            )
            self.assertEqual(
                [record.video_id for record in module.load_video_records(csv_path)],
                ["yyyyyyyyyyy"],
            )

    def test_load_video_records_many_deduplicates_across_files(self):
        module = _load_downloader_module()

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            first = root / "first.csv"
            second = root / "second.csv"
            for path, rows in [
                (
                    first,
                    [
                        {"vid_id": "aaaaaaaaaaa", "vid_url": "https://youtube.com/watch?v=aaaaaaaaaaa"},
                        {"vid_id": "bbbbbbbbbbb", "vid_url": "https://youtube.com/watch?v=bbbbbbbbbbb"},
                    ],
                ),
                (
                    second,
                    [
                        {"id": "bbbbbbbbbbb", "url": "https://youtube.com/watch?v=bbbbbbbbbbb"},
                        {"id": "ccccccccccc", "url": "https://youtube.com/watch?v=ccccccccccc"},
                    ],
                ),
            ]:
                with path.open("w", newline="", encoding="utf-8") as handle:
                    writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
                    writer.writeheader()
                    writer.writerows(rows)

            records = module.load_video_records_many([first, second])

            self.assertEqual(
                [record.video_id for record in records],
                ["aaaaaaaaaaa", "bbbbbbbbbbb", "ccccccccccc"],
            )

    def test_build_ytdlp_command_prefers_480p_and_uses_archive_sleep_and_rate_limit(self):
        module = _load_downloader_module()

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            command = module.build_ytdlp_command(
                video_id="dQw4w9WgXcQ",
                output_root=root,
                min_sleep=60,
                max_sleep=180,
                sleep_requests=2,
                limit_rate="3M",
                retries=5,
                cookies_from_browser="firefox",
                cookies_file=None,
                remote_components="ejs:npm",
            )

            command_text = " ".join(command)

            self.assertIn("bestvideo[height=480]+bestaudio", command_text)
            self.assertIn("bestvideo[height<=480]+bestaudio", command_text)
            self.assertIn("--newline", command)
            self.assertIn("--cookies-from-browser", command)
            self.assertIn("firefox", command)
            self.assertIn("--remote-components", command)
            self.assertIn("ejs:npm", command)
            self.assertIn("--download-archive", command)
            self.assertIn(str(root / "archive" / "video_archive.txt"), command)
            self.assertIn("--sleep-interval", command)
            self.assertIn("60", command)
            self.assertIn("--max-sleep-interval", command)
            self.assertIn("180", command)
            self.assertIn("--limit-rate", command)
            self.assertIn("3M", command)
            self.assertIn("-o", command)
            self.assertIn(str(root / "videos" / "%(id)s.%(ext)s"), command)

    def test_build_ytdlp_transcript_command_downloads_subtitles_only(self):
        module = _load_downloader_module()

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            command = module.build_ytdlp_transcript_command(
                video_id="dQw4w9WgXcQ",
                output_root=root,
                languages=["en-orig", "en", "en.*"],
                subtitle_format="json3/vtt/best",
                sleep_requests=1,
                sleep_subtitles=2,
                retries=5,
                cookies_from_browser="firefox",
                cookies_file=None,
                remote_components="ejs:npm",
            )

            self.assertIn("--skip-download", command)
            self.assertIn("--write-subs", command)
            self.assertIn("--write-auto-subs", command)
            self.assertIn("--sub-format", command)
            self.assertIn("json3/vtt/best", command)
            self.assertIn("--cookies-from-browser", command)
            self.assertIn("firefox", command)
            self.assertIn("--remote-components", command)
            self.assertIn("ejs:npm", command)
            self.assertIn(str(root / "transcripts_raw" / "%(id)s.%(ext)s"), command)

    def test_cached_transcript_is_not_fetched_again(self):
        module = _load_downloader_module()

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            transcript_dir = root / "transcripts"
            transcript_dir.mkdir()
            cached = [{"text": "hello", "start": 0.0, "duration": 1.0}]
            (transcript_dir / "dQw4w9WgXcQ.json").write_text(
                json.dumps(cached),
                encoding="utf-8",
            )

            def fail_if_called(*_args, **_kwargs):
                raise AssertionError("fetcher should not be called when cache exists")

            result = module.fetch_transcript_with_cache(
                video_id="dQw4w9WgXcQ",
                transcript_dir=transcript_dir,
                languages=["en"],
                fetcher=fail_if_called,
                min_sleep=0,
                max_sleep=0,
                backoff_seconds=[],
            )

            self.assertEqual(result.status, "cached")
            self.assertEqual(result.path, transcript_dir / "dQw4w9WgXcQ.json")

    def test_ytdlp_transcript_cache_skips_existing_normalized_file(self):
        module = _load_downloader_module()

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            module.ensure_output_dirs(root)
            cached_path = root / "transcripts" / "dQw4w9WgXcQ.json"
            cached_path.write_text(
                json.dumps([{"text": "cached", "start": 0.0, "duration": 1.0}]),
                encoding="utf-8",
            )

            def fail_if_called(*_args, **_kwargs):
                raise AssertionError("runner should not be called when cache exists")

            result = module.download_transcript_with_ytdlp_cache(
                video_id="dQw4w9WgXcQ",
                output_root=root,
                languages=["en"],
                subtitle_format="json3",
                min_sleep=0,
                max_sleep=0,
                sleep_requests=1,
                sleep_subtitles=2,
                retries=5,
                dry_run=False,
                force=False,
                cookies_from_browser=None,
                cookies_file=None,
                remote_components=None,
                runner=fail_if_called,
            )

            self.assertEqual(result.status, "cached")
            self.assertEqual(result.path, cached_path)
            archive_text = (root / "archive" / "transcript_archive.txt").read_text(
                encoding="utf-8"
            )
            self.assertIn("youtube dQw4w9WgXcQ", archive_text)

    def test_ytdlp_json3_transcript_is_normalized(self):
        module = _load_downloader_module()

        class Completed:
            returncode = 0
            stdout = "subtitle downloaded"
            stderr = ""

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            module.ensure_output_dirs(root)

            def fake_runner(_command, **_kwargs):
                raw_path = root / "transcripts_raw" / "dQw4w9WgXcQ.en-orig.json3"
                raw_path.write_text(
                    json.dumps(
                        {
                            "events": [
                                {
                                    "tStartMs": 1200,
                                    "dDurationMs": 800,
                                    "segs": [{"utf8": "hello "}, {"utf8": "world"}],
                                }
                            ]
                        }
                    ),
                    encoding="utf-8",
                )
                return Completed()

            result = module.download_transcript_with_ytdlp_cache(
                video_id="dQw4w9WgXcQ",
                output_root=root,
                languages=["en"],
                subtitle_format="json3",
                min_sleep=0,
                max_sleep=0,
                sleep_requests=1,
                sleep_subtitles=2,
                retries=5,
                dry_run=False,
                force=False,
                cookies_from_browser=None,
                cookies_file=None,
                remote_components=None,
                runner=fake_runner,
            )

            self.assertEqual(result.status, "downloaded")
            rows = json.loads((root / "transcripts" / "dQw4w9WgXcQ.json").read_text())
            self.assertEqual(rows, [{"text": "hello world", "start": 1.2, "duration": 0.8}])
            archive_text = (root / "archive" / "transcript_archive.txt").read_text(
                encoding="utf-8"
            )
            self.assertIn("youtube dQw4w9WgXcQ", archive_text)

    def test_force_transcript_preserves_existing_file_when_download_fails(self):
        module = _load_downloader_module()

        class Completed:
            returncode = 1
            stdout = ""
            stderr = "failed"

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            module.ensure_output_dirs(root)
            cached_path = root / "transcripts" / "dQw4w9WgXcQ.json"
            original_rows = [{"text": "keep me", "start": 0.0, "duration": 1.0}]
            cached_path.write_text(json.dumps(original_rows), encoding="utf-8")

            def fake_runner(_command, **_kwargs):
                return Completed()

            result = module.download_transcript_with_ytdlp_cache(
                video_id="dQw4w9WgXcQ",
                output_root=root,
                languages=["en"],
                subtitle_format="json3",
                min_sleep=0,
                max_sleep=0,
                sleep_requests=1,
                sleep_subtitles=2,
                retries=5,
                dry_run=False,
                force=True,
                cookies_from_browser=None,
                cookies_file=None,
                remote_components=None,
                runner=fake_runner,
            )

            self.assertEqual(result.status, "failed")
            self.assertEqual(json.loads(cached_path.read_text()), original_rows)

    def test_sleep_random_swaps_min_and_max_before_sleeping(self):
        module = _load_downloader_module()
        calls = []

        original_uniform = module.random.uniform
        original_sleep = module.time.sleep
        try:
            module.random.uniform = lambda low, high: calls.append((low, high)) or 7
            module.time.sleep = lambda seconds: calls.append(("sleep", seconds))

            module.sleep_random(15, 5)
        finally:
            module.random.uniform = original_uniform
            module.time.sleep = original_sleep

        self.assertEqual(calls, [(5, 15), ("sleep", 7)])

    def test_download_video_writes_ytdlp_log(self):
        module = _load_downloader_module()

        class Completed:
            returncode = 3
            stdout = "out text"
            stderr = "err text"

        def fake_runner(command, **kwargs):
            self.assertEqual(kwargs["text"], True)
            self.assertEqual(kwargs["capture_output"], True)
            self.assertIn("-m", command)
            self.assertIn("yt_dlp", command)
            return Completed()

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            module.ensure_output_dirs(root)

            result = module.download_video(
                video_id="dQw4w9WgXcQ",
                output_root=root,
                min_sleep=60,
                max_sleep=180,
                sleep_requests=2,
                limit_rate="3M",
                retries=5,
                dry_run=False,
                cookies_from_browser=None,
                cookies_file=None,
                remote_components=None,
                runner=fake_runner,
            )

            self.assertEqual(result.return_code, 3)
            self.assertEqual(result.status, "failed")
            self.assertEqual(result.log_path, root / "logs" / "dQw4w9WgXcQ_yt_dlp.log")
            log_text = result.log_path.read_text(encoding="utf-8")
            self.assertIn("STDOUT:\nout text", log_text)
            self.assertIn("STDERR:\nerr text", log_text)

    def test_download_video_handles_missing_ytdlp(self):
        module = _load_downloader_module()

        def missing_runner(_command, **_kwargs):
            raise FileNotFoundError("yt-dlp")

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            module.ensure_output_dirs(root)

            result = module.download_video(
                video_id="dQw4w9WgXcQ",
                output_root=root,
                min_sleep=60,
                max_sleep=180,
                sleep_requests=2,
                limit_rate="3M",
                retries=5,
                dry_run=False,
                cookies_from_browser=None,
                cookies_file=None,
                remote_components=None,
                runner=missing_runner,
            )

            self.assertEqual(result.return_code, 127)
            self.assertEqual(result.status, "failed")
            self.assertIn("pip install yt-dlp", result.error)
            self.assertIn("pip install yt-dlp", result.log_path.read_text(encoding="utf-8"))

    def test_build_artifact_payload_includes_trace_metadata(self):
        module = _load_downloader_module()
        record = module.VideoRecord(
            video_id="dQw4w9WgXcQ",
            source="videos.csv:2",
            row={
                "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "vid_title": "Lecture title",
                "timestamp": "00:10:00",
                "question_id": "q1",
            },
        )

        payload = module.build_artifact_payload(
            kind="video",
            record=record,
            status="downloaded",
            return_code=0,
        )

        self.assertEqual(payload["video_id"], "dQw4w9WgXcQ")
        self.assertEqual(payload["url"], "https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        self.assertEqual(payload["title"], "Lecture title")
        self.assertEqual(payload["timestamp"], "00:10:00")
        self.assertEqual(payload["question_id"], "q1")


if __name__ == "__main__":
    unittest.main()
