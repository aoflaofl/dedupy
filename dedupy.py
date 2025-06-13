#!/usr/bin/env python3

"""Identify duplicate files."""

import argparse
import datetime
import hashlib
import json
import os
from collections import Counter
import logging


def setup_logging(debug: bool):
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(level=level, format="%(asctime)s - %(levelname)s - %(message)s")


def add_file_to_size_map(
    fullname: str,
    file_count: Counter[tuple[int, int]],
    size_filename_dict: dict[int, list[str]],
    args: argparse.Namespace,
):
    try:
        stat_obj = os.stat(fullname)
    except (PermissionError, FileNotFoundError):
        return
    file_id = (stat_obj.st_dev, stat_obj.st_ino)
    if file_count[file_id] == 0:
        file_count[file_id] += 1
        file_size = stat_obj.st_size
        if not (args.ignore_zero_length and file_size == 0):
            size_filename_dict.setdefault(file_size, []).append(fullname)


def process_directory(
    start_dir: str,
    file_count: Counter[tuple[int, int]],
    size_filename_dict: dict[int, list[str]],
    args: argparse.Namespace,
):
    for path, dirs, files in os.walk(start_dir):
        if not args.include_hidden_files:
            dirs[:] = [d for d in dirs if not d.startswith(".")]
        for filename in files:
            if args.include_hidden_files or not filename.startswith("."):
                fullname = os.path.realpath(os.path.join(path, filename))
                add_file_to_size_map(fullname, file_count, size_filename_dict, args)


def group_files_by_size(
    items: list[str], args: argparse.Namespace
) -> dict[int, list[str]]:
    file_count: Counter[tuple[int, int]] = Counter()
    size_filename_dict: dict[int, list[str]] = {}

    for item in items:
        if os.path.isdir(item):
            process_directory(item, file_count, size_filename_dict, args)
        else:
            add_file_to_size_map(item, file_count, size_filename_dict, args)

    return size_filename_dict


def hash_list_of_files(
    list_of_filenames: list[str],
    hash_func_name: str,
    chunk_size_multiplier: int = 128,
    sample_size: int = 8192,
) -> dict[str, list[str]]:
    """
    Hash a list of files to identify potential duplicates using a two-pass approach.

    First, a quick hash is computed from the beginning of each file (using `sample_size` bytes).
    Files with matching quick hashes are then fully hashed (using the specified hash function and chunk size).
    Only files with matching quick hashes are fully hashed to improve performance.

    Args:
        list_of_filenames (list[str]): List of file paths to hash.
        hash_func_name (str): Name of the hash function to use (e.g., 'sha1', 'md5').
        chunk_size_multiplier (int, optional): Multiplier for the hash function's block size to determine read chunk size. Defaults to 128.
        sample_size (int, optional): Number of bytes to read from the start of each file for the quick hash. Defaults to 8192.

    Returns:
        dict[str, list[str]]: Dictionary mapping full file hashes to lists of filenames that share that hash (potential duplicates).
    """
    logging.debug(
        "Hashing files with %s (chunk size: %d, sample size: %d)",
        hash_func_name,
        chunk_size_multiplier,
        sample_size,
    )
    # First pass: Quick hash of file beginnings
    quick_hash_map: dict[str, list[str]] = {}
    for filename in list_of_filenames:
        try:
            hash_obj = hashlib.new(hash_func_name)
            with open(filename, "rb") as f:
                chunk = f.read(sample_size)
                hash_obj.update(chunk)
            quick_digest = hash_obj.hexdigest() + "_quick"
            quick_hash_map.setdefault(quick_digest, []).append(filename)
        except (PermissionError, FileNotFoundError) as e:
            logging.warning("Error processing file %s: %s", filename, e)
            continue
        except Exception as e:
            logging.error("Unexpected error with file %s: %s", filename, e)
            continue

    # Second pass: Full hash for files with matching quick hashes
    map_hash_to_file_list: dict[str, list[str]] = {}
    for _, similar_files in quick_hash_map.items():
        if len(similar_files) > 1:  # Only process potential duplicates
            for filename in similar_files:
                try:
                    hash_obj = hashlib.new(hash_func_name)
                    with open(filename, "rb") as f:
                        while chunk := f.read(128 * hash_obj.block_size):
                            hash_obj.update(chunk)
                    digest = hash_obj.hexdigest()
                    map_hash_to_file_list.setdefault(digest, []).append(filename)
                except (PermissionError, FileNotFoundError) as e:
                    logging.warning("Error processing file %s: %s", filename, e)
                    continue
                except Exception as e:
                    logging.error("Unexpected error with file %s: %s", filename, e)
                    continue

    return map_hash_to_file_list


def remove_single_member_groups(
    dic: dict[object, list[str]],
) -> dict[object, list[str]]:
    return {key: value for (key, value) in dic.items() if len(value) > 1}


def hash_file_list(
    list_of_files: list[str], hash_func_name: str, args: argparse.Namespace
) -> dict[str, list[str]]:
    logging.debug("Num files to hash: %d", len(list_of_files))

    start_time = datetime.datetime.now()
    out = hash_list_of_files(list_of_files, hash_func_name, args.chunk_size_multiplier)

    if args.debug:
        elapsed_time = datetime.datetime.now() - start_time
        logging.debug("Hashing time: %s", elapsed_time)

    return remove_single_member_groups(out)


def print_file_clusters(
    files_grouped_by_size: dict[int, list[str]],
    digest_algorithms: list[str],
    args: argparse.Namespace,
) -> None:
    cluster = 1
    save_out_dict: dict[str, list[str]] = {}
    for key, file_list in files_grouped_by_size.items():
        out_dict = generate_hash_dict_from_list(file_list, digest_algorithms, args)
        if args.save:
            save_out_dict.update(out_dict)
        for hash_key, filenames in out_dict.items():
            print(
                f"{len(filenames)} files in cluster {cluster} ({key} bytes, digest {hash_key})"
            )
            for filename in filenames:
                print(filename)
            cluster += 1
    if args.save:
        save_dict_to_json(save_out_dict, args.save)
        print(f"Saved output to {args.save}")


def generate_hash_dict_from_list(
    file_list: list[str], digest_algorithms: list[str], args: argparse.Namespace
) -> dict[str, list[str]]:
    out_dict = hash_file_list(file_list, digest_algorithms[0], args)

    for hash_func_name in digest_algorithms[1:]:
        new_out_dict: dict[str, list[str]] = {}
        for new_file_list in out_dict.values():
            new_out_dict.update(hash_file_list(new_file_list, hash_func_name, args))
        out_dict = new_out_dict

    return out_dict


def save_dict_to_json(dictionary: dict[str, list[str]], filename: str) -> None:
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(dictionary, f, indent=2, ensure_ascii=False)


def list_of_digest_algorithms(arg: str) -> list[str]:
    """Parse a comma-separated list of hash algorithms."""
    hash_algorithms = arg.split(",")
    for algo in hash_algorithms:
        if algo not in hashlib.algorithms_guaranteed:
            raise ValueError(f"Invalid hash function: {algo}")
    return hash_algorithms


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        epilog=f"Allowed digest algorithms: {hashlib.algorithms_guaranteed}"
    )
    parser.add_argument(
        "-z",
        "--zero",
        action="store_true",
        help="Ignore zero length files.",
        default=False,
        dest="ignore_zero_length",
    )
    parser.add_argument(
        "-a",
        "--all",
        action="store_true",
        help="Include hidden files and directories",
        default=False,
        dest="include_hidden_files",
    )
    parser.add_argument(
        "--debug", action="store_true", help="Debug output", default=False
    )
    parser.add_argument(
        "items",
        nargs="+",
        help="Files or directories to process.  Directories are processed recursively.",
    )
    parser.add_argument(
        "-d",
        "--digest",
        metavar="ALGORITHM[,ALGORITHM,...]",
        help="Specify the digest algorithms to use (default: sha1)",
        type=list_of_digest_algorithms,
        dest="digest_algorithms",
        default=["sha1"],
    )
    parser.add_argument(
        "-s",
        "--save",
        help="Save the final output as a JSON file",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=128,
        help="Chunk size multiplier for file reading (default: 128)",
        dest="chunk_size_multiplier",
    )

    args = parser.parse_args()

    return args


def get_possible_duplicates_by_size(
    items: list[str], args: argparse.Namespace
) -> dict[int, list[str]]:
    file_groups = group_files_by_size(items, args)
    return remove_single_member_groups(file_groups)


def main():
    start_time = datetime.datetime.now()

    args = parse_arguments()
    setup_logging(args.debug)

    logging.debug("Starting dedupy")
    logging.debug("Arguments: %s", args)

    dupe_dict = get_possible_duplicates_by_size(args.items, args)
    print_file_clusters(dupe_dict, args.digest_algorithms, args)

    end_time = datetime.datetime.now()
    elapsed_time = end_time - start_time
    logging.debug("Total running time: %s", elapsed_time)


if __name__ == "__main__":
    main()
