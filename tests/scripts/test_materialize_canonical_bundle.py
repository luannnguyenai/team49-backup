from pathlib import Path

import pytest

from scripts.materialize_canonical_bundle import download_bundle, parse_s3_uri, relative_key_path


def test_parse_s3_uri_rejects_non_s3_scheme():
    with pytest.raises(ValueError):
        parse_s3_uri("https://example.com/bundle")


def test_parse_s3_uri_requires_prefix():
    with pytest.raises(ValueError):
        parse_s3_uri("s3://bucket-only")


def test_parse_s3_uri_normalizes_bucket_and_prefix():
    assert parse_s3_uri("s3://bundle-bucket/canonical-bundles/v1/canonical/") == (
        "bundle-bucket",
        "canonical-bundles/v1/canonical",
    )


def test_relative_key_path_maps_object_under_prefix():
    assert relative_key_path(
        "canonical-bundles/v1/canonical",
        "canonical-bundles/v1/canonical/question_bank.jsonl",
    ) == Path("question_bank.jsonl")


def test_relative_key_path_rejects_root_marker():
    with pytest.raises(ValueError):
        relative_key_path("canonical-bundles/v1/canonical", "canonical-bundles/v1/canonical")


def test_download_bundle_requires_objects(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    class FakePaginator:
        def paginate(self, **_: object):
            yield {}

    class FakeS3Client:
        def get_paginator(self, name: str):
            assert name == "list_objects_v2"
            return FakePaginator()

    class FakeBoto3Module:
        @staticmethod
        def client(name: str):
            assert name == "s3"
            return FakeS3Client()

    monkeypatch.setitem(__import__("sys").modules, "boto3", FakeBoto3Module())

    with pytest.raises(FileNotFoundError, match="No bundle files found"):
        download_bundle(s3_uri="s3://bundle-bucket/canonical-bundles/v1/canonical", output_dir=tmp_path)


def test_download_bundle_requires_manifest(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    class FakePaginator:
        def paginate(self, **_: object):
            yield {
                "Contents": [
                    {
                        "Key": "canonical-bundles/v1/canonical/question_bank.jsonl",
                        "Size": 12,
                    }
                ]
            }

    class FakeS3Client:
        def get_paginator(self, name: str):
            assert name == "list_objects_v2"
            return FakePaginator()

        def download_file(self, bucket: str, key: str, destination: str):
            assert bucket == "bundle-bucket"
            assert key.endswith("question_bank.jsonl")
            Path(destination).write_text("{}", encoding="utf-8")

    class FakeBoto3Module:
        @staticmethod
        def client(name: str):
            assert name == "s3"
            return FakeS3Client()

    monkeypatch.setitem(__import__("sys").modules, "boto3", FakeBoto3Module())

    with pytest.raises(FileNotFoundError, match="manifest.json"):
        download_bundle(s3_uri="s3://bundle-bucket/canonical-bundles/v1/canonical", output_dir=tmp_path)


def test_download_bundle_materializes_manifest(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    objects = {
        "canonical-bundles/v1/canonical/manifest.json": '{"version":"v1"}',
        "canonical-bundles/v1/canonical/question_bank.jsonl": '{"id":1}\n',
    }

    class FakePaginator:
        def paginate(self, **_: object):
            yield {
                "Contents": [{"Key": key, "Size": len(value)} for key, value in objects.items()]
            }

    class FakeS3Client:
        def get_paginator(self, name: str):
            assert name == "list_objects_v2"
            return FakePaginator()

        def download_file(self, bucket: str, key: str, destination: str):
            assert bucket == "bundle-bucket"
            Path(destination).write_text(objects[key], encoding="utf-8")

    class FakeBoto3Module:
        @staticmethod
        def client(name: str):
            assert name == "s3"
            return FakeS3Client()

    monkeypatch.setitem(__import__("sys").modules, "boto3", FakeBoto3Module())

    report = download_bundle(
        s3_uri="s3://bundle-bucket/canonical-bundles/v1/canonical",
        output_dir=tmp_path,
    )

    assert report["downloaded_files"] == 2
    assert (tmp_path / "manifest.json").read_text(encoding="utf-8") == '{"version":"v1"}'
    assert (tmp_path / "question_bank.jsonl").read_text(encoding="utf-8") == '{"id":1}\n'
