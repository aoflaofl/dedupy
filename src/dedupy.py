"""
Identify duplicate files.

Adapted from a sample script by Randall Hettinger.
"""

import argparse
import hashlib
import os
from pprint import pprint


def add_file_to_size_map(fullname, size_filenames_dict, ignore_zero_len=True):
    """Map a single file."""
    try:
        file_size = os.stat(fullname).st_size

        if ignore_zero_len is True and file_size == 0:
            return

        size_filenames_dict.setdefault(file_size, []).append(fullname)
    except (PermissionError, FileNotFoundError):
        # TODO: Optionally report error
        pass


def group_files_by_size(start_dir, size_filenames_dict, ignore_zero_len=True):
    """
    Create a dict of files mapped to size.

    By default ignore zero length files.
    """
    for path, _, files in os.walk(start_dir):
        for filename in files:
            fullname = os.path.join(path, filename)
            add_file_to_size_map(fullname, size_filenames_dict, ignore_zero_len)


def process_command_line_items(cli_items, ignore_zero_len=True):
    """Handle command line items."""
    size_filename_dict = {}
    for thing in cli_items:
        # TODO: Make work with symbolic links
        if os.path.exists(thing):
            if os.path.isdir(thing):
                group_files_by_size(thing, size_filename_dict, ignore_zero_len)
            else:
                add_file_to_size_map(thing, size_filename_dict, ignore_zero_len)
    return size_filename_dict


def hash_list_of_files(list_of_filenames, hash_func_name):
    """Take a list of files and group them by a hash function."""
    hash_files = {}
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


def remove_non_duplicates(dic):
    """
    Create a new dict without entries that don't have duplicates.

    Takes a dict with the key shared by
    all files in the list.
    """
    return {key: value for (key, value) in dic.items() if len(value) > 1}


def group_files_by_hash_function(dic, hash_list):
    """Group files in each list by hash value, discarding non-duplicates."""
    # pprint(hashlib.algorithms_guaranteed)
    for hash_name in hash_list:
        pprint("Hashing using " + hash_name + " algorithm.")
        out_dict = {}
        for file_list in dic.values():
            hash_dict = hash_list_of_files(file_list, hash_name)
            some_other_dict = remove_non_duplicates(hash_dict)
            out_dict.update(some_other_dict)
        dic = out_dict
    return out_dict


def print_grouped_files(dic):
    """Print the file groups."""
    pprint(dic)


if __name__ == "__main__":
    PARSER = argparse.ArgumentParser()
    PARSER.add_argument("items", nargs="+")
    ARGS = PARSER.parse_args()

    _DIC = process_command_line_items(ARGS.items)
    _DIC = remove_non_duplicates(_DIC)
    print_grouped_files(
        group_files_by_hash_function(
            _DIC, ["md5", "sha1", "sha224", "sha256", "sha384", "sha512"]
        )
    )
