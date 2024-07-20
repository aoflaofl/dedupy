#!/usr/bin/env python3

"""Identify duplicate files.

Adapted from a sample script by Randall Hettinger.
"""

import argparse
import datetime
import hashlib
import json
import os
from collections import Counter


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
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for filename in files:
            if not filename.startswith("."):
                fullname = os.path.realpath(os.path.join(path, filename))
                add_file_to_size_map(fullname, file_count, size_filename_dict, args)


def group_files_by_size(items: list, args) -> dict:
    file_count = Counter()
    size_filename_dict = {}
    
    for item in items:
        if os.path.exists(item):
            if os.path.isdir(item):
                process_directory(item, file_count, size_filename_dict, args)
            else:
                add_file_to_size_map(item, file_count, size_filename_dict, args)
    
    return size_filename_dict


def hash_list_of_files(list_of_filenames: list, hash_func_name: str) -> dict:
    hash_files: dict = {}
    for filename in list_of_filenames:

        try:
            f = open(filename, "rb")
        except (PermissionError, FileNotFoundError):
            continue

        with f:
            hash_obj = hashlib.new(hash_func_name)
            hash_obj.update(f.read())
            digest = hash_obj.hexdigest()

            hash_files.setdefault(digest, []).append(filename)

    return hash_files


def remove_non_duplicates(dic: dict) -> dict:
    return {key: value for (key, value) in dic.items() if len(value) > 1}


def hash_file_list(list_of_files: list, hash_list: list, args) -> dict:
    if args.debug:
        print("Num files to hash: ", len(list_of_files))

    start_time = datetime.datetime.now()
    out = hash_list_of_files(list_of_files, hash_list[0])

    if args.debug:
        end_time = datetime.datetime.now()
        elapsed_time = end_time - start_time
        print("Hashing time: ", elapsed_time)

    out = remove_non_duplicates(out)

    return out


def print_file_clusters(_dic: dict, args) -> None:
    cluster = 1
    for key, file_list in _dic.items():
        out_dict = hash_file_list(file_list, ["md5"], args)
        for hashkey, filenames in out_dict.items():
            print(f"{len(filenames)} files in cluster {cluster} ({key} bytes, digest {hashkey})")
            for filename in filenames:
                print(filename)
            cluster += 1


def save_dict_to_json(dictionary: dict, filename: str) -> None:
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(dictionary, f)


def parse_arguments():
    parser = argparse.ArgumentParser()
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
    )
    parser.add_argument("--debug", action="store_true", help="Debug output", default=False)
    parser.add_argument("items", nargs="+", help="Files or directories to process.")

    args = parser.parse_args()

    if args.debug:
        print("Arguments: ", args)

    return args


def find_duplicates(items: list, args) -> dict:
    file_groups = group_files_by_size(items, args)
    return remove_non_duplicates(file_groups)


def main():
    args = parse_arguments()

    for i in hashlib.algorithms_available:
        print(i)

    dupe_dict = find_duplicates(args.items, args)
    print_file_clusters(dupe_dict, args)


if __name__ == "__main__":
    main()
