def normalize_path(path: str) -> str:
    while "//" in path:
        path = path.replace("//", "/")
    return path
