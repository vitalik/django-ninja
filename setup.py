import sys

sys.stderr.write(
    """
===============================
Unsupported installation method
===============================
django-ninja does not install with `python setup.py install`.
Please use `python -m pip install` instead.
"""
)
sys.exit(1)
