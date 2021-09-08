import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__))))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tests/demo_project"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "demo.settings")

# from django.conf import settings
# settings.configure()
import django  # noqa

django.setup()


def pytest_generate_tests(metafunc):
    os.environ["NINJA_SKIP_REGISTRY"] = "yes"
