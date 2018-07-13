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
    _DIC = group_files_by_size("/Users/gejohann/Dropbox/Gooble")
    print_grouped_files(
        group_files_by_hash_function(
            _DIC, ["md5", "sha1", "sha224", "sha256", "sha384", "sha512"]
        )
    )
