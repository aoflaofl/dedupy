"""
Adapted from a sample script by Randall Hettinger.
"""

import hashlib
import os
from pprint import pprint


def group_files_by_size(start_dir=".", ignore_zero_len=True):
    """
    Create a dict of files mapped to size.  By default ignore zero length files.
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

    return size_filenames_dict


def hash_list_of_files(list_of_files):
    """
    Take a list of files and group them by a hash function.
    """
    hash_files = {}
    for filename in list_of_files:
        try:
            d = open(filename, "rb").read()
        except:
            continue

        h = hashlib.sha1(d).hexdigest()
        # pprint((h, filename))
        hash_files.setdefault(h, []).append(filename)

    return hash_files


dic = group_files_by_size("/")
for size, file_list in dic.items():
    if len(file_list) > 1:
        # pprint(size)
        # pprint(file_list)
        newdic = hash_list_of_files(file_list)
        pprint({key: value for key, value in newdic.items() if len(value) > 1})

# pprint(hashmap)
