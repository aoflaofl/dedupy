# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

**Install dev dependencies:**
```bash
pip install -r requirements-dev.txt --break-system-packages
```

> `pytest` installs to `~/.local/bin/` which may not be on PATH. Use `~/.local/bin/pytest` or add it to PATH.

**Run all tests with coverage:**
```bash
~/.local/bin/pytest
```

**Run a single test:**
```bash
~/.local/bin/pytest test/test_dedupy.py::test_duplicate_detection_groups_by_hash
```

**Run tests without coverage:**
```bash
~/.local/bin/pytest --no-cov
```

**Run the tool:**
```bash
python3 dedupy.py [options] <files/directories>
```

## Architecture

`dedupy.py` is a single-file CLI tool with no external runtime dependencies (stdlib only). It finds duplicate files using a two-pass hashing strategy:

1. **Size grouping** — `group_files_by_size()` / `get_possible_duplicates_by_size()` group files by `st_size`, discarding unique-size files immediately.
2. **Quick hash** — `quick_hash_list_of_files()` hashes only the first `sample_size` bytes (default 8192) of each candidate, further filtering the set.
3. **Full hash** — `finalize_full_hashes()` hashes remaining candidates in full using chunked reads.

Hard links are tracked via `(st_dev, st_ino)` tuples to avoid counting the same inode twice.

**Key functions:**
- `compute_file_hash()` — core hash function; supports partial reads and multiple algorithms
- `hash_list_of_files()` — orchestrates the two-pass strategy
- `generate_hash_dict_from_list()` — groups filenames by hash, supports multiple digest algorithms
- `parse_arguments()` — CLI entry point; algorithms validated against `hashlib.algorithms_available`

**Tests** live in `test/`, with fixtures in `test/conftest.py`. The `make_args()` helper constructs `argparse.Namespace` objects for unit tests. Sample files (`a`, `b`, `c`, `d->c`, `.one`, etc.) are checked into `test/` as test data.

**pytest.ini** configures `--cov=dedupy --cov-report=term-missing` by default, so coverage runs automatically with every `pytest` invocation.
