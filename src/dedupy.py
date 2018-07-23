"""
Identify duplicate files.

Adapted from a sample script by Randall Hettinger.
"""

import argparse
import hashlib
import os
import time
from collections import Counter
from pprint import pprint


def group_files_by_size(items: list) -> dict:
    """Build a map of file sizes as key and list of files of that size as value."""
    file_count: Counter = Counter()

    def add_file_to_size_map(
        fullname: str, size_filenames: dict, ignore_zero_len: bool = True
    ) -> None:
        """Map a single file."""
        try:
            stat_obj = os.stat(fullname)
            file_id = (stat_obj.st_dev, stat_obj.st_ino)
            file_count[file_id] += 1
            if file_count[file_id] > 1:
                return
            file_size = stat_obj.st_size

            if ignore_zero_len is True and file_size == 0:
                return

            size_filenames.setdefault(file_size, []).append(fullname)
        except (PermissionError, FileNotFoundError):
            # TODO: Optionally report error
            pass

    def walk_directories_for_size(
        start_dir: str, size_filenames: dict, ignore_zero_len: bool = True
    ) -> None:
        """
        Create a dict of files mapped to size.

        By default ignore zero length files.
        """
        for path, _, files in os.walk(start_dir):
            for filename in files:
                fullname = os.path.relpath(os.path.join(path, filename))
                add_file_to_size_map(fullname, size_filenames, ignore_zero_len)

    def process_command_line_items(
        cli_items: list, ignore_zero_len: bool = True
    ) -> dict:
        """Handle command line items."""
        size_filename_dict: dict = {}
        for thing in cli_items:
            # TODO: Make work with symbolic links.  Turn links into real paths and make
            # sure they only get scanned once.
            if os.path.exists(thing):
                if os.path.isdir(thing):
                    walk_directories_for_size(
                        thing, size_filename_dict, ignore_zero_len
                    )
                else:
                    add_file_to_size_map(thing, size_filename_dict, ignore_zero_len)
        return size_filename_dict

    return process_command_line_items(items)


def hash_list_of_files(list_of_filenames: list, hash_func_name: str) -> dict:
    """Take a list of files and group them by a hash function."""
    hash_files: dict = {}
    for filename in list_of_filenames:

        try:
            data = open(filename, "rb").read()
        except (PermissionError, FileNotFoundError):
            continue

        hash_obj = hashlib.new(hash_func_name)
        hash_obj.update(data)
        digest = hash_obj.hexdigest()
        # pprint((h, filename))
        hash_files.setdefault(digest, []).append(filename)

    return hash_files


def remove_non_duplicates(dic: dict) -> dict:
    """
    Create a new dict without entries that don't have duplicates.

    Takes a dict with the key shared by
    all files in the list.
    """
    return {key: value for (key, value) in dic.items() if len(value) > 1}


def group_files_by_hash_function(dic: dict, hash_list: list) -> dict:
    """Group files in each list by hash value, discarding non-duplicates."""
    # pprint(hashlib.algorithms_guaranteed)
    for hash_name in hash_list:
        length = len(dic)
        pprint(
            "Hashing " + str(length) + " clusters using " + hash_name + " algorithm."
        )
        out_dict = {}
        for file_list in dic.values():
            hash_dict = hash_list_of_files(file_list, hash_name)
            some_other_dict = remove_non_duplicates(hash_dict)
            out_dict.update(some_other_dict)
        dic = out_dict
    return out_dict


def print_grouped_files(dic: dict) -> None:
    """Print the file groups."""
    for key in dic:
        print(key)
        for file in dic[key]:
            print(file)


if __name__ == "__main__":
    PARSER = argparse.ArgumentParser()
    PARSER.add_argument("items", nargs="+")
    ARGS = PARSER.parse_args()

    print("Start time: " + str(time.time()))
    _DIC = group_files_by_size(ARGS.items)
    print("Clusters: " + str(len(_DIC)))
    _DIC = remove_non_duplicates(_DIC)
    print_grouped_files(
        group_files_by_hash_function(
            # _DIC, ["md5", "sha1", "sha224", "sha256", "sha384", "sha512"]
            _DIC,
            ["md5", "sha384", "sha512"],
        )
    )
    print("End time: " + str(time.time()))
