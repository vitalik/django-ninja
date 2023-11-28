import os
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent.resolve()

sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests/demo_project"))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "demo.settings")

import django  # noqa

django.setup()


def pytest_generate_tests(metafunc):
    os.environ["NINJA_SKIP_REGISTRY"] = "yes"
