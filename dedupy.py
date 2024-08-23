#!/usr/bin/env python3

"""Identify duplicate files."""

import argparse
import datetime
import hashlib
import json
import os
from collections import Counter
import logging


def setup_logging(debug):
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(level=level, format="%(asctime)s - %(levelname)s - %(message)s")


def add_file_to_size_map(
    fullname: str,
    file_count: Counter,
    size_filename_dict: dict,
    args,
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
    file_count: Counter,
    size_filename_dict: dict,
    args,
):
    for path, dirs, files in os.walk(start_dir):
        if not args.include_hidden_files:
            dirs[:] = [d for d in dirs if not d.startswith(".")]
        for filename in files:
            if args.include_hidden_files or not filename.startswith("."):
                fullname = os.path.realpath(os.path.join(path, filename))
                add_file_to_size_map(fullname, file_count, size_filename_dict, args)


def group_files_by_size(items: list, args) -> dict:
    file_count = Counter()
    size_filename_dict = {}

    for item in items:
        if os.path.isdir(item):
            process_directory(item, file_count, size_filename_dict, args)
        else:
            add_file_to_size_map(item, file_count, size_filename_dict, args)

    return size_filename_dict


def hash_list_of_files(list_of_filenames: list, hash_func_name: str) -> dict:
    map_hash_to_file_list: dict = {}
    for filename in list_of_filenames:
        try:
            hash_obj = hashlib.new(hash_func_name)
            with open(filename, "rb") as f:
                while chunk := f.read(128 * hash_obj.block_size):
                    hash_obj.update(chunk)
                digest = hash_obj.hexdigest()

                map_hash_to_file_list.setdefault(digest, []).append(filename)
        except (PermissionError, FileNotFoundError):
            continue

    return map_hash_to_file_list


def remove_single_member_groups(dic: dict) -> dict:
    return {key: value for (key, value) in dic.items() if len(value) > 1}


def hash_file_list(list_of_files: list, hash_func_name: str, args) -> dict:
    logging.debug("Num files to hash: %d", len(list_of_files))

    start_time = datetime.datetime.now()
    out = hash_list_of_files(list_of_files, hash_func_name)

    if args.debug:
        elapsed_time = datetime.datetime.now() - start_time
        logging.debug("Hashing time: %s", elapsed_time)

    return remove_single_member_groups(out)


def print_file_clusters(files_grouped_by_size: dict, digest_algorithms: list, args) -> None:
    cluster = 1
    for key, file_list in files_grouped_by_size.items():
        out_dict = generate_hash_dict_from_list(file_list, digest_algorithms, args)
        for hash_key, filenames in out_dict.items():
            print(f"{len(filenames)} files in cluster {cluster} ({key} bytes, digest {hash_key})")
            for filename in filenames:
                print(filename)
            cluster += 1


def generate_hash_dict_from_list(file_list: list, digest_algorithms: list, args) -> dict:
    out_dict = hash_file_list(file_list, digest_algorithms[0], args)

    for hash_func_name in digest_algorithms[1:]:
        new_out_dict = {}
        for new_file_list in out_dict.values():
            new_out_dict.update(hash_file_list(new_file_list, hash_func_name, args))
        out_dict = new_out_dict

    return out_dict


def save_dict_to_json(dictionary: dict, filename: str) -> None:
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(dictionary, f)


def list_of_digest_algorithms(arg):
    hash_algorithms = arg.split(",")
    for algo in hash_algorithms:
        if algo not in hashlib.algorithms_guaranteed:
            raise ValueError(f"Invalid hash function: {algo}")
    return hash_algorithms


def parse_arguments():
    parser = argparse.ArgumentParser(
        epilog="Allowed digest algorithms: %s" % hashlib.algorithms_guaranteed
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
    parser.add_argument("--debug", action="store_true", help="Debug output", default=False)
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

    args = parser.parse_args()

    return args


def get_possible_duplicates_by_size(items: list, args) -> dict:
    file_groups = group_files_by_size(items, args)
    out = remove_single_member_groups(file_groups)
    return out


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
