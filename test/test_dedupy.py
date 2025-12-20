import argparse
import hashlib
from pathlib import Path

import pytest

from dedupy import (
    DEFAULT_SAMPLE_SIZE,
    compute_file_hash,
    generate_hash_dict_from_list,
    get_possible_duplicates_by_size,
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
