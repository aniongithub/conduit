import os

def get_filename(f: str) -> str:
    # Get only the filename part of the string
    return os.path.basename(f)

def get_extension(f: str) -> str:
    # Get only the extension part of the string
    return os.path.splitext(f)[1]

def get_basename(f: str) -> str:
    # Get only the basename part of the string
    return os.path.splitext(os.path.basename(f))[0]

def get_dirname(f: str) -> str:
    # Get only the dirname part of the string
    return os.path.dirname(f)

def get_stem(f: str) -> str:
    # Get only the stem part of the string
    return os.path.splitext(os.path.basename(f))[0]

def get_abspath(f: str) -> str:
    # Get only the abspath part of the string
    return os.path.abspath(f)

def get_realpath(f: str) -> str:
    # Get only the realpath part of the string
    return os.path.realpath(f)

def get_relpath(f: str) -> str:
    # Get only the relpath part of the string
    return os.path.relpath(f)

def get_normpath(f: str) -> str:
    # Get only the normpath part of the string
    return os.path.normpath(f)

def get_filename_without_extension(f: str) -> str:
    # Get only the filename without extension part of the string
    return os.path.splitext(f)[0]

def get_functions() -> dict[str, callable]:
    # Find all functions in this module and return them as a dictionary
    return {name: obj for name, obj in globals().items() if callable(obj) and name.startswith("get_")}
