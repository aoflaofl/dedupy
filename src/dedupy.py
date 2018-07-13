"""
Identify duplicate files.

Adapted from a sample script by Randall Hettinger.
"""

import hashlib
import os
from pprint import pprint


def group_files_by_size(start_dir=".", ignore_zero_len=True):
    """
    Create a dict of files mapped to size.

    By default ignore zero length files.
    """
    size_filenames_dict = {}  # content signature -> list of matching filenames

    for path, _, files in os.walk(start_dir):
        for filename in files:
            fullname = os.path.join(path, filename)
            try:
                file_size = os.stat(fullname).st_size

                if ignore_zero_len is True and file_size == 0:
                    continue

                size_filenames_dict.setdefault(file_size, []).append(fullname)
            except (PermissionError, FileNotFoundError):
                pass

    return remove_non_duplicates(size_filenames_dict)


def hash_list_of_files(list_of_files, hash_func=hashlib.sha1):
    """Take a list of files and group them by a hash function."""
    hash_files = {}
    for filename in list_of_files:
        try:
            data = open(filename, "rb").read()
        except (PermissionError, FileNotFoundError):
            continue

        hsh = hash_func(d).hexdigest()
        # pprint((h, filename))
        hash_files.setdefault(hsh, []).append(filename)

    return hash_files


def remove_non_duplicates(dic):
    """
    Create a new dict without entries that don't have duplicates.

    Takes a dict with the key shared by
    all files in the list.
    """
    return {key: value for (key, value) in dic.items() if len(value) > 1}


def group_files_by_hash_function(dic):
    """Group files in each list by hash value, discarding non-duplicates."""
    out_dict = {}
    for file_list in dic.values():
        hash_dict = hash_list_of_files(file_list)
        some_other_dict = remove_non_duplicates(hash_dict)
        out_dict.update(some_other_dict)
    return out_dict


if __name__ == "__main__":
    _DIC = group_files_by_size(".")
    pprint(group_files_by_hash_function(_DIC))
