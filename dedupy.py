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

VERBOSE = False


def add_file_to_size_map(fullname: str, file_count: Counter, size_filename_dict: dict,
                         ignore_zero_len: bool = True):
    """Add a file to the size mapping if it meets certain conditions.

    This function attempts to add a file, identified by its full path, to a mapping of file sizes to
    lists of file paths. It first checks if the file exists and can be accessed. If so, it checks if
    the file has already been counted (to handle hard links correctly). If the file is new or has
    not
    been added yet, it checks the file size and, based on the ignore_zero_len flag, decides whether
    to add the file to the size mapping.

    Args:
        fullname (str): The full path of the file to be added.
        file_count (Counter): A Counter object tracking the occurrence of each file based on its
                              inode and device ID, to handle hard links.
        size_filename_dict (dict): A dictionary mapping file sizes to lists of file paths.
        ignore_zero_len (bool, optional): If True, files with zero length are not added to the
                                          mapping. Defaults to True.
    """
    try:
        stat_obj = os.stat(fullname)
    except (PermissionError, FileNotFoundError):
        return
    file_id = (stat_obj.st_dev, stat_obj.st_ino)
    if file_count[file_id] == 0:
        file_count[file_id] += 1
        file_size = stat_obj.st_size
        if not (ignore_zero_len and file_size == 0):
            size_filename_dict.setdefault(file_size, []).append(fullname)


def process_directory(start_dir: str, file_count: Counter, size_filename_dict: dict,
                      ignore_zero_len: bool = True):
    """Process a directory and its subdirectories to map files by size.

    This function walks through the directory specified by start_dir, including all subdirectories,
    and processes each file that does not start with a dot ('.'). It adds each file to a size
    mapping
    unless the file is of zero length and ignore_zero_len is True. This helps in identifying
    potential
    duplicate files based on their size.

    Args:
        start_dir (str): The starting directory path to begin processing.
        file_count (Counter): A Counter object to track occurrences of each file based on its inode
        and device ID.
        size_filename_dict (dict): A dictionary mapping file sizes to lists of file paths.
        ignore_zero_len (bool, optional): If True, files with zero length are ignored. Defaults to
        True.
    """
    for path, dirs, files in os.walk(start_dir):
        dirs[:] = [d for d in dirs if
                   not d.startswith('.')]  # Exclude directories starting with '.'
        for filename in files:
            if not filename.startswith('.'):  # Exclude files starting with '.'
                fullname = os.path.realpath(os.path.join(path, filename))
                add_file_to_size_map(fullname, file_count, size_filename_dict, ignore_zero_len)


def process_items(items: list, file_count: Counter, size_filename_dict: dict,
                  ignore_zero_len: bool = True):
    """Process each item in the provided list of paths.

    This function iterates over a list of file or directory paths. For each path, it checks if the
    path exists.
    If the path is a directory, it processes the directory and its contents. If the path is a file,
    it adds the
    file to the size mapping. This function supports the option to ignore files of zero length.

    Args:
        items (list): A list of file or directory paths to process.
        file_count (Counter): A Counter object to track the occurrence of each file.
        size_filename_dict (dict): A dictionary mapping file sizes to lists of file paths.
        ignore_zero_len (bool, optional): A flag to indicate whether to ignore files of zero length.
        Defaults to True.
    """
    for item in items:
        if os.path.exists(item):
            if os.path.isdir(item):
                process_directory(item, file_count, size_filename_dict, ignore_zero_len)
            else:
                add_file_to_size_map(item, file_count, size_filename_dict, ignore_zero_len)


def group_files_by_size(items: list) -> dict:
    """Group files by their size.

    This function processes a list of file paths, grouping them by their size. It uses a counter to
    track the occurrence of each file (identified by device and inode numbers to handle hard links
    correctly) and a dictionary to associate file sizes with lists of file paths. Files with the
    same size are considered potential duplicates and are grouped together in the dictionary. This
    function is a preliminary step in identifying duplicate files based on their size before further
    processing for exact matches.

    Args:
        items (list): A list of file paths to be grouped by size.

    Returns:
        dict: A dictionary where keys are file sizes and values are lists of file paths that have
        that size.
    """
    file_count = Counter()  # Tracks occurrence of each file to handle hard links.
    size_filename_dict = {}  # Maps file sizes to lists of file paths.
    process_items(items, file_count, size_filename_dict)  # Process each item in the provided list.
    return size_filename_dict  # Return the dictionary grouping files by size.


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

    if VERBOSE:
        print("Num files to hash: ", len(list_of_files))

    start_time = datetime.datetime.now()
    out = hash_list_of_files(list_of_files, hash_list[0])

    if VERBOSE:
        end_time = datetime.datetime.now()
        elapsed_time = end_time - start_time
        print("Hashing time: ", elapsed_time)

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


def save_dict_to_json(dictionary: dict, filename: str) -> None:
    """Save a dictionary to a JSON file.

    This function takes a dictionary and saves it to a JSON file with the specified filename.
    It opens the file in write mode and uses json.dump() to write the dictionary contents to the
    file.

    Args:
        dictionary (dict): The dictionary to be saved to the JSON file.
        filename (str): The name of the file to save the JSON data to.

    Note:
        This function will overwrite the file if it already exists.
    """
    with open(filename, 'w', encoding="utf-8") as f:
        json.dump(dictionary, f)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-z", "--zero", action="store_true", help="Include zero length files.")
    parser.add_argument("-d", "--dot", action="store_true",
                        help="Include '.' files and directories")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument("items", nargs="+")
    args = parser.parse_args()

    if args.verbose:
        VERBOSE = True
        print("Arguments: ", args)

    _DIC = group_files_by_size(args.items)

    save_dict_to_json(_DIC, 'file_sizes.json', )

    _DIC = remove_non_duplicates(_DIC)

    save_dict_to_json(_DIC, 'file_sizes_clean.json', )

    print_file_clusters(_DIC)
