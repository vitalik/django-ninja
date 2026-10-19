import os
import subprocess
import sys

from django.test import override_settings

from ninja.conf import settings


def test_default_configuration():
    assert settings.PAGINATION_CLASS == "ninja.pagination.LimitOffsetPagination"
    assert settings.PAGINATION_PER_PAGE == 100


def test_override_settings_updates_ninja_settings():
    assert settings.NUM_PROXIES is None
    assert settings.PAGINATION_PER_PAGE == 100

    with override_settings(NINJA_NUM_PROXIES=3, NINJA_PAGINATION_PER_PAGE=20):
        assert settings.NUM_PROXIES == 3
        assert settings.PAGINATION_PER_PAGE == 20

    assert settings.NUM_PROXIES is None
    assert settings.PAGINATION_PER_PAGE == 100


def test_importing_ninja_does_not_import_django_test():
    # ninja is imported by production code; django.test pulls in the whole test
    # framework (Client, TestCase, unittest) and is stripped from some slim
    # deployment images.
    code = (
        "import os, sys, django;"
        "os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'demo.settings');"
        "django.setup();"
        "import ninja;"
        "sys.exit(1 if 'django.test' in sys.modules else 0)"
    )
    env = {**os.environ, "PYTHONPATH": os.pathsep.join(sys.path)}
    assert subprocess.run([sys.executable, "-c", code], env=env).returncode == 0
