import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from unittest.mock import patch

import pytest

from dedupy import (
    DEFAULT_SAMPLE_SIZE,
    add_file_to_size_map,
    compute_file_hash,
    generate_hash_dict_from_list,
    get_possible_duplicates_by_size,
    hash_file_list,
    list_of_digest_algorithms,
    main,
    parse_arguments,
    print_file_clusters,
    save_dict_to_json,
)


def make_args(**overrides):
    """Build a minimal argparse.Namespace compatible with dedupy helpers."""
    base = dict(
        ignore_zero_length=False,
        include_hidden_files=False,
        chunk_size_multiplier=128,
        sample_size=DEFAULT_SAMPLE_SIZE,
        debug=False,
        save=None,
    )
    base.update(overrides)
    return argparse.Namespace(**base)


def write_file(path: Path, content: bytes = b"data") -> Path:
    path.write_bytes(content)
    return path


def test_duplicate_detection_groups_by_hash(tmp_path: Path):
    args = make_args()

    file_a = write_file(tmp_path / "a.txt", b"same content")
    file_b = write_file(tmp_path / "b.txt", b"same content")
    write_file(tmp_path / "unique.txt", b"unique")

    size_groups = get_possible_duplicates_by_size([tmp_path], args)
    assert len(size_groups) == 1

    file_size, files = next(iter(size_groups.items()))
    digest_map = generate_hash_dict_from_list(file_size, files, ["sha1"], args)

    assert len(digest_map) == 1
    digest, duplicates = next(iter(digest_map.items()))
    assert set(duplicates) == {str(file_a), str(file_b)}
    assert digest == hashlib.sha1(b"same content").hexdigest()


def test_hidden_files_respected(tmp_path: Path):
    hidden = write_file(tmp_path / ".hidden", b"dup")
    write_file(tmp_path / ".hidden_copy", b"dup")

    args_skip_hidden = make_args(include_hidden_files=False)
    size_groups = get_possible_duplicates_by_size([tmp_path], args_skip_hidden)
    assert size_groups == {}

    args_include_hidden = make_args(include_hidden_files=True)
    size_groups_hidden = get_possible_duplicates_by_size([tmp_path], args_include_hidden)
    assert len(size_groups_hidden) == 1

    file_size, files = next(iter(size_groups_hidden.items()))
    digest_map = generate_hash_dict_from_list(file_size, files, ["sha1"], args_include_hidden)
    duplicates = next(iter(digest_map.values()))
    assert set(duplicates) == {str(hidden), str(hidden.with_name(".hidden_copy"))}


def test_zero_length_files_can_be_ignored(tmp_path: Path):
    write_file(tmp_path / "zero1", b"")
    write_file(tmp_path / "zero2", b"")

    args_ignore = make_args(ignore_zero_length=True)
    assert get_possible_duplicates_by_size([tmp_path], args_ignore) == {}

    args_include = make_args(ignore_zero_length=False)
    size_groups = get_possible_duplicates_by_size([tmp_path], args_include)
    assert len(size_groups) == 1


def test_chunked_hash_matches_full_hash(tmp_path: Path):
    content = b"abcdefg" * 200  # long enough for multiple chunks
    file_path = write_file(tmp_path / "chunked.dat", content)

    full = compute_file_hash(str(file_path), "sha1")
    chunked = compute_file_hash(str(file_path), "sha1", read_size=64, chunked=True)
    assert full == chunked


# --- compute_file_hash error path ---

def test_compute_file_hash_missing_file():
    result = compute_file_hash("/nonexistent/path/file.txt", "sha1")
    assert result is None


# --- add_file_to_size_map error paths ---

def test_add_file_to_size_map_nonexistent_file():
    file_count: Counter = Counter()
    size_map: dict = {}
    args = make_args()
    add_file_to_size_map("/nonexistent/file.txt", file_count, size_map, args)
    assert size_map == {}


def test_add_file_to_size_map_permission_error(tmp_path: Path):
    file_count: Counter = Counter()
    size_map: dict = {}
    args = make_args()
    with patch("dedupy.os.stat", side_effect=PermissionError):
        add_file_to_size_map(str(tmp_path / "file.txt"), file_count, size_map, args)
    assert size_map == {}


# --- plain-file input to group_files_by_size ---

def test_group_files_by_size_with_plain_files(tmp_path: Path):
    file_a = write_file(tmp_path / "a.txt", b"same content")
    file_b = write_file(tmp_path / "b.txt", b"same content")
    args = make_args()
    size_groups = get_possible_duplicates_by_size([str(file_a), str(file_b)], args)
    assert len(size_groups) == 1
    file_size, files = next(iter(size_groups.items()))
    assert set(files) == {str(file_a), str(file_b)}


# --- hash_file_list debug timing branch ---

def test_hash_file_list_with_debug(tmp_path: Path):
    file_a = write_file(tmp_path / "a.txt", b"dup")
    file_b = write_file(tmp_path / "b.txt", b"dup")
    args = make_args(debug=True)
    result = hash_file_list(3, [str(file_a), str(file_b)], "sha1", args)
    assert len(result) == 1
    assert set(next(iter(result.values()))) == {str(file_a), str(file_b)}


# --- print_file_clusters ---

def test_print_file_clusters_prints_duplicates(tmp_path: Path, capsys):
    file_a = write_file(tmp_path / "a.txt", b"same content")
    file_b = write_file(tmp_path / "b.txt", b"same content")
    write_file(tmp_path / "unique.txt", b"unique")
    args = make_args()
    size_groups = get_possible_duplicates_by_size([str(tmp_path)], args)
    print_file_clusters(size_groups, ["sha1"], args)
    out = capsys.readouterr().out
    assert "2 files in cluster 1" in out
    assert str(file_a) in out
    assert str(file_b) in out


def test_print_file_clusters_saves_json(tmp_path: Path, capsys):
    file_a = write_file(tmp_path / "a.txt", b"same content")
    file_b = write_file(tmp_path / "b.txt", b"same content")
    save_path = str(tmp_path / "output.json")
    args = make_args(save=save_path)
    size_groups = get_possible_duplicates_by_size([str(tmp_path)], args)
    print_file_clusters(size_groups, ["sha1"], args)
    out = capsys.readouterr().out
    assert f"Saved output to {save_path}" in out
    data = json.loads(Path(save_path).read_text())
    assert len(data) == 1
    assert set(next(iter(data.values()))) == {str(file_a), str(file_b)}


# --- generate_hash_dict_from_list with multiple algorithms ---

def test_generate_hash_dict_multiple_algorithms(tmp_path: Path):
    file_a = write_file(tmp_path / "a.txt", b"same content")
    file_b = write_file(tmp_path / "b.txt", b"same content")
    args = make_args()
    result = generate_hash_dict_from_list(
        len(b"same content"), [str(file_a), str(file_b)], ["sha1", "sha256"], args
    )
    assert len(result) == 1
    assert set(next(iter(result.values()))) == {str(file_a), str(file_b)}


# --- save_dict_to_json ---

def test_save_dict_to_json(tmp_path: Path):
    save_path = tmp_path / "out.json"
    data = {"abc123": ["file1.txt", "file2.txt"]}
    save_dict_to_json(data, str(save_path))
    assert json.loads(save_path.read_text()) == data


# --- list_of_digest_algorithms ---

def test_list_of_digest_algorithms_valid():
    assert list_of_digest_algorithms("sha1,sha256") == ["sha1", "sha256"]


def test_list_of_digest_algorithms_invalid():
    with pytest.raises(ValueError, match="Invalid hash function"):
        list_of_digest_algorithms("sha1,notarealalgorithm")


# --- parse_arguments ---

def test_parse_arguments_defaults(monkeypatch):
    monkeypatch.setattr("sys.argv", ["dedupy.py", "/some/path"])
    args = parse_arguments()
    assert args.items == ["/some/path"]
    assert args.digest_algorithms == ["sha1"]
    assert args.ignore_zero_length is False
    assert args.include_hidden_files is False
    assert args.debug is False
    assert args.save is None
    assert args.chunk_size_multiplier == 128
    assert args.sample_size == DEFAULT_SAMPLE_SIZE


def test_parse_arguments_flags(monkeypatch):
    monkeypatch.setattr("sys.argv", ["dedupy.py", "-z", "-a", "--debug", "/p"])
    args = parse_arguments()
    assert args.ignore_zero_length is True
    assert args.include_hidden_files is True
    assert args.debug is True


def test_parse_arguments_digest_and_save(monkeypatch, tmp_path: Path):
    save_path = str(tmp_path / "out.json")
    monkeypatch.setattr(
        "sys.argv", ["dedupy.py", "-d", "sha256", "-s", save_path, "/p"]
    )
    args = parse_arguments()
    assert args.digest_algorithms == ["sha256"]
    assert args.save == save_path


# --- finalize_full_hashes / hash_list_of_files large-file path ---

@pytest.mark.parametrize("content_a,content_b,expect_dup", [
    (b"duplicate content", b"duplicate content", True),
    (b"sameXXXXXX", b"sameYYYYYY", False),
])
def test_full_hash_path(tmp_path: Path, content_a: bytes, content_b: bytes, expect_dup: bool):
    # sample_size=4 forces the file_size >= sample_size branch for content > 4 bytes
    file_a = write_file(tmp_path / "a.txt", content_a)
    file_b = write_file(tmp_path / "b.txt", content_b)
    args = make_args(sample_size=4)
    result = hash_file_list(len(content_a), [str(file_a), str(file_b)], "sha1", args)
    if expect_dup:
        assert len(result) == 1
        assert set(next(iter(result.values()))) == {str(file_a), str(file_b)}
    else:
        assert result == {}


# --- main ---

def test_main(tmp_path: Path, monkeypatch, capsys):
    write_file(tmp_path / "a.txt", b"dup content")
    write_file(tmp_path / "b.txt", b"dup content")
    monkeypatch.setattr("sys.argv", ["dedupy.py", str(tmp_path)])
    main()
    out = capsys.readouterr().out
    assert "2 files in cluster 1" in out
