import sys

# docs examples use modern syntax (list[...], X | None)
if sys.version_info[:2] < (3, 10):
    collect_ignore_glob = ["test_*.py"]
