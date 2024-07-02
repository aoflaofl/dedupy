#!/usr/bin/env python3

"""Identify duplicate files.

Adapted from a sample script by Randall Hettinger.
"""

import argparse
import datetime
import hashlib
import os
from collections import Counter
from pprint import pprint


def group_files_by_size(items: list) -> dict:
    """Build a dict with file sizes as keys and a list of files of that size as value.

    Obviously only files of the same size can be duplicates so this is the first
    step to remove non-duplicates from further processing.
    """
    file_count: Counter = Counter()
    size_filename_dict: dict = {}

    def add_file_to_size_map(fullname: str, ignore_zero_len: bool = True) -> None:
        """Map a single file."""

        try:
            stat_obj = os.stat(fullname)
        except (PermissionError, FileNotFoundError):
            # TODO: Optionally report error
            return

        file_id = (stat_obj.st_dev, stat_obj.st_ino)
        if file_count[file_id] > 0:
            return
        file_count[file_id] += 1
        file_size = stat_obj.st_size
        if not (ignore_zero_len and file_size == 0):
            size_filename_dict.setdefault(file_size, []).append(fullname)

    def process_directory(start_dir: str, ignore_zero_len: bool = True) -> None:
        """Process a directory and its subdirectories."""
        for path, dirs, files in os.walk(start_dir):
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            for filename in (f for f in files if not f.startswith('.')):
                fullname = os.path.relpath(os.path.join(path, filename))
                add_file_to_size_map(fullname, ignore_zero_len)

    def process_items(ignore_zero_len: bool = True) -> None:
        """Process command line items."""
        for item in items:
            if os.path.exists(item):
                if os.path.isdir(item):
                    process_directory(item, ignore_zero_len)
                else:
                    add_file_to_size_map(item, ignore_zero_len)

    process_items()
    return size_filename_dict


def hash_list_of_files(list_of_filenames: list, hash_func_name: str) -> dict:
    """Take a list of files and group them by a hash function."""
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
            # pprint((h, filename))
            hash_files.setdefault(digest, []).append(filename)

    return hash_files


def remove_non_duplicates(dic: dict) -> dict:
    """Create a new dict without entries that don't have duplicates.

    Takes a dict with the key shared by
    all files in the list.
    """
    return {key: value for (key, value) in dic.items() if len(value) > 1}


def hash_file_list(list_of_files: list, hash_list: list) -> dict:
    """Hash a list of files using the first hash algorithm from the provided list.

    This function takes a list of files and a list of hash algorithms, uses the first
    hash algorithm to hash the files, and then removes any non-duplicate entries.

    Args:
        list_of_files (list): A list of file paths to be hashed.
        hash_list (list): A list of hash algorithm names. Only the first one is used.

    Returns:
        dict: A dictionary where keys are hash digests and values are lists of file paths
              that share the same hash. Only entries with more than one file are included.

    Note:
        This function uses the first hash algorithm in hash_list, even if multiple are provided.
    """
    out = hash_list_of_files(list_of_files, hash_list[0])
    out = remove_non_duplicates(out)
    return out


def print_file_clusters(_dic: dict) -> None:
    """Print clusters of duplicate files grouped by size and hash.

    This function iterates through a dictionary of file sizes and their corresponding
    file lists. For each size group, it further hashes the files using SHA1 and
    prints information about each cluster of identical files.

    Prints:
        For each cluster of identical files:
        - Number of files in the cluster
        - Cluster number
        - File size in bytes
        - SHA1 digest of the files
        - List of file paths in the cluster
    """
    cluster = 1
    for key, file_list in _dic.items():
        out_dict = hash_file_list(file_list, ["sha1"])
        for hashkey, filenames in out_dict.items():
            print(f'{len(filenames)} files in cluster {cluster} ({key} bytes, digest {hashkey})')
            for filename in filenames:
                print(filename)
            cluster += 1


if __name__ == "__main__":
    PARSER = argparse.ArgumentParser()
    # TODO: Implement include zero length files.
    PARSER.add_argument("-z", "--zero", action="store_true", help="Include zero length files.")
    # TODO: Implement include of dot files and directories
    PARSER.add_argument("-d", "--dot", action="store_true", help="Include '.' files and directories")
    PARSER.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    PARSER.add_argument("items", nargs="+")
    ARGS = PARSER.parse_args()

    pprint(ARGS)

    if ARGS.verbose:
        print("Start time: ", datetime.datetime.now())

    _DIC = group_files_by_size(ARGS.items)

    if ARGS.verbose:
        print("Raw file size clusters: " + str(len(_DIC)))

    _DIC = remove_non_duplicates(_DIC)

    if ARGS.verbose:
        print("Non-duplicate file clusters: " + str(len(_DIC)))

    print_file_clusters(_DIC)
    # _DIC = group_files_by_hash_function(
    # _DIC, ["md5", "sha1", "sha224", "sha256", "sha384", "sha512"]
    #        _DIC,
    # ["md5", "sha384", "sha512"],
    #       ["md5"]
    # )
    # print_grouped_files(_DIC)

    if ARGS.verbose:
        print("End time: ", datetime.datetime.now())
