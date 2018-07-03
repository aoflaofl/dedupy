import hashlib
import os
from pprint import pprint


def group_files_by_size(start_dir=".", ignore_zero_len=True):

    # Search a directory tree for all files with duplicate content
    size_filenames_dict = {}  # content signature -> list of matching filenames

    for path, _, files in os.walk(start_dir):
        for filename in files:
            fullname = os.path.join(path, filename)
            file_size = os.stat(fullname).st_size
            if ignore_zero_len == True and file_size == 0:
                continue

            size_filenames_dict.setdefault(file_size, []).append(fullname)

    return size_filenames_dict


def hash_list_of_files(list_of_files):
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


dic = group_files_by_size("C:/")
for size, file_list in dic.items():
    if len(file_list) > 1:
        # pprint(size)
        # pprint(file_list)
        newdic = hash_list_of_files(file_list)
        pprint({key: value for key, value in newdic.items() if len(value) > 1})

# pprint(hashmap)
