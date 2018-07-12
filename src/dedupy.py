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


def hash_list_of_files(list_of_files):
    """Take a list of files and group them by a hash function."""
    hash_files = {}
    for filename in list_of_files:
        try:
            data = open(filename, "rb").read()
        except (PermissionError, FileNotFoundError):
            continue

        hsh = hashlib.sha1(data).hexdigest()
        # pprint((h, filename))
        hash_files.setdefault(hsh, []).append(filename)

    return hash_files


def remove_non_duplicates(dic):
    """
    Create a new dict without entries that don't have duplicates.

    Takes a dict with the key shared by
    all files in the list.
    """
    new_dic = {}
    for size, file_list in dic.items():
        if len(file_list) > 1:
            new_dic[size] = file_list
    return new_dic


if __name__ == "__main__":
    _DIC = group_files_by_size(".")
    pprint(_DIC)
