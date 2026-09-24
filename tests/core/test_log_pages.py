from pathlib import Path

import pytest

from waterology.core.log_pages import read_log_page


def test_pages_reconstruct_unicode_without_loss(tmp_path: Path):
    path = tmp_path / "log"
    original = "a\u00e9\U0001f30a\n" * 100
    path.write_text(original)
    offset = 0
    pages = []
    while True:
        result = read_log_page(path, offset=offset, max_bytes=7)
        assert len(result["content"].encode()) <= 7
        pages.append(result["content"])
        if result["next_offset"] is None:
            break
        assert result["next_offset"] > offset
        offset = result["next_offset"]
    assert "".join(pages) == original


def test_search_paginates_without_missing_boundary_match(tmp_path: Path):
    path = tmp_path / "log"
    path.write_bytes(b"x" * (1024 * 1024 - 2) + b"ERROR old failure\n" + b"z" * 100)
    first = read_log_page(path, query="ERROR", max_bytes=32)
    assert first["match_found"] is False
    second = read_log_page(path, offset=first["next_offset"], query="ERROR", max_bytes=32)
    assert second["match_found"] is True
    assert second["content"].startswith("ERROR old failure")


def test_snapshot_rejects_changed_file(tmp_path: Path):
    path = tmp_path / "log"
    path.write_text("abcdef")
    first = read_log_page(path, max_bytes=4)
    path.write_text("updated contents")
    with pytest.raises(ValueError, match="changed"):
        read_log_page(path, offset=4, snapshot=first["snapshot"])


@pytest.mark.parametrize(
    "kwargs", [{"max_bytes": 0}, {"max_bytes": 65537}, {"offset": -1}, {"query": ""}]
)
def test_invalid_options(tmp_path, kwargs):
    path = tmp_path / "log"
    path.write_text("hello")
    with pytest.raises(ValueError):
        read_log_page(path, **kwargs)


def test_reject_symlink(tmp_path):
    original = tmp_path / "original"
    original.write_text("private")
    link = tmp_path / "link"
    link.symlink_to(original)
    with pytest.raises(ValueError, match="symlink"):
        read_log_page(link)


def test_one_character_search_continues_after_full_scan(tmp_path):
    path = tmp_path / "log"
    path.write_bytes(b"x" * (1024 * 1024 + 20) + b"!")
    first = read_log_page(path, query="!")
    assert first["next_offset"] > 0
    second = read_log_page(path, query="!", offset=first["next_offset"])
    assert second["content"] == "!"
    assert second["next_offset"] is None


def test_empty_file_and_no_match(tmp_path):
    path = tmp_path / "log"
    path.write_text("")
    assert read_log_page(path)["next_offset"] is None
    path.write_text("ordinary progress")
    result = read_log_page(path, query="ERROR")
    assert result["content"] == ""
    assert result["match_found"] is False
    assert result["next_offset"] is None


def test_invalid_utf8_has_explicit_replacement_and_byte_offsets(tmp_path):
    path = tmp_path / "log"
    path.write_bytes(b"abc\xffde")
    page = read_log_page(path, max_bytes=4)
    assert page["content"] == "abc\ufffd"
    assert page["next_offset"] == 4
    assert read_log_page(path, offset=4)["content"] == "de"
