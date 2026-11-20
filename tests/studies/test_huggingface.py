import asyncio
import json
from urllib.parse import urlparse

import pytest
from mcp import Client
from typer.testing import CliRunner

import waterology.mcp.server as server_module
from waterology.cli import app


def _mock_hf_opener(monkeypatch, payloads):
    import urllib.request

    requests = []
    queue = list(payloads)

    class Response:
        def __init__(self, body: bytes):
            self._body = body

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def read(self, size=-1):
            return self._body[:size] if size >= 0 else self._body

    class Opener:
        def open(self, request, timeout):
            assert timeout == 30
            requests.append(request)
            body = queue.pop(0) if len(queue) > 1 else queue[0]
            if isinstance(body, (dict, list)):
                body = json.dumps(body).encode("utf-8")
            elif isinstance(body, str):
                body = body.encode("utf-8")
            return Response(body)

    monkeypatch.setattr(urllib.request, "build_opener", lambda *args: Opener())
    return requests


def test_hf_dataset_info_files_and_small_text_read(monkeypatch):
    from waterology.core import huggingface

    monkeypatch.setenv("HF_TOKEN", "HF_SECRET_TOKEN")
    dataset_payload = {
        "id": "org/hydro-bench",
        "sha": "abcdef123456",
        "private": False,
        "gated": False,
        "disabled": False,
        "downloads": 42,
        "likes": 5,
        "usedStorage": 102400,
        "lastModified": "2025-08-01T00:00:00.000Z",
        "tags": ["license:cc-by-4.0", "task_categories:time-series-forecasting"],
        "siblings": [{"rfilename": "README.md"}, {"rfilename": "data/train.parquet"}],
        "cardData": {
            "license": "cc-by-4.0",
            "configs": [{"config_name": "default"}],
            "dataset_info": {
                "features": [{"name": "flow_cfs", "dtype": "float64"}],
                "splits": [{"name": "train", "num_examples": 1000}],
            },
        },
    }
    tree_payload = [
        {"path": "README.md", "type": "file", "size": 128},
        {"path": "data/train.parquet", "type": "file", "size": 999999, "lfs": {"oid": "sha256:1"}},
    ]
    readme_text = "# Hydro Bench\nStreamflow benchmark.\n"
    requests = _mock_hf_opener(monkeypatch, [dataset_payload, tree_payload, readme_text])

    info = huggingface.hf_dataset_info("org/hydro-bench")
    assert info["id"] == "org/hydro-bench"
    assert info["license"] == "cc-by-4.0"
    assert info["sibling_count"] == 2
    assert info["dataset_info"]["splits"][0]["name"] == "train"
    assert requests[0].get_header("Authorization") == "Bearer HF_SECRET_TOKEN"
    assert "HF_SECRET_TOKEN" not in str(info)

    files = huggingface.hf_repo_files("org/hydro-bench")
    assert urlparse(requests[1].full_url).path == "/api/datasets/org/hydro-bench/tree/main"
    assert files["files"] == [
        {"path": "README.md", "type": "file", "size": 128, "lfs": False},
        {"path": "data/train.parquet", "type": "file", "size": 999999, "lfs": True},
    ]

    read = huggingface.hf_repo_read_file("org/hydro-bench", "README.md", max_bytes=1024)
    assert urlparse(requests[2].full_url).path == "/datasets/org/hydro-bench/raw/main/README.md"
    assert read["content"] == readme_text
    assert read["truncated"] is False


def test_hf_large_text_truncation_and_revision_encoding(monkeypatch):
    from waterology.core import huggingface

    # File larger than 262 KiB must truncate cleanly at max_bytes instead of failing,
    # and multibyte UTF-8 split at max_bytes must report exact decoded byte length.
    prefix = b"a" * 9 + "é".encode() + b"z" * 300_000  # 'é' spans bytes 9..10
    requests = _mock_hf_opener(monkeypatch, [prefix])
    read = huggingface.hf_repo_read_file(
        "org/hydro-bench", "README.md", revision="refs/convert/parquet", max_bytes=10
    )
    assert "refs%2Fconvert%2Fparquet" in requests[0].full_url
    assert read["truncated"] is True
    assert read["content"] == "aaaaaaaaa"
    assert read["returned_bytes"] == 9


def test_hf_rejects_traversal_and_binary_payloads(monkeypatch):
    from waterology.core import huggingface

    with pytest.raises(ValueError, match="Invalid repository"):
        huggingface.hf_dataset_info("../escape")
    with pytest.raises(ValueError, match="Invalid file path"):
        huggingface.hf_repo_read_file("org/hydro-bench", "../secrets.txt")

    _mock_hf_opener(monkeypatch, [b"PAR1\x00\x01\x02binary"])
    with pytest.raises(ValueError, match="binary"):
        huggingface.hf_repo_read_file("org/hydro-bench", "data/train.parquet")


def test_hf_cli_and_mcp_tools(tmp_path, monkeypatch):
    from waterology.core import huggingface

    monkeypatch.setattr(
        huggingface,
        "hf_dataset_info",
        lambda repo_id, revision="main": {"id": repo_id, "revision": revision, "usable": True},
    )
    monkeypatch.setattr(
        huggingface,
        "hf_repo_files",
        lambda repo_id, repo_type="dataset", revision="main", path="", limit=200: {
            "repo_id": repo_id,
            "files": [{"path": "README.md", "type": "file", "size": 10, "lfs": False}],
        },
    )
    monkeypatch.setattr(
        huggingface,
        "hf_repo_read_file",
        lambda repo_id, file_path, repo_type="dataset", revision="main", max_bytes=65536: {
            "repo_id": repo_id,
            "path": file_path,
            "content": "hello\n",
            "truncated": False,
        },
    )

    cli = CliRunner().invoke(app, ["hf-dataset-info", "org/hydro-bench"])
    assert cli.exit_code == 0, cli.output
    assert "org/hydro-bench" in cli.output

    async def exercise():
        server = server_module.create_server()
        async with Client(server, raise_exceptions=True) as client:
            listed = await client.list_tools()
            names = {t.name for t in listed.tools}
            assert {"hf_dataset_info", "hf_repo_files", "hf_repo_read_file"} <= names
            info = await client.call_tool("hf_dataset_info", {"repo_id": "org/hydro-bench"})
            assert info.structured_content == {
                "ok": True,
                "result": {"id": "org/hydro-bench", "revision": "main", "usable": True},
            }
            read = await client.call_tool(
                "hf_repo_read_file", {"repo_id": "org/hydro-bench", "file_path": "README.md"}
            )
            assert read.structured_content["result"]["content"] == "hello\n"

    asyncio.run(exercise())
