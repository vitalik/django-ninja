import json
import os
import tempfile
from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from ninja.management.commands.export_openapi_schema import Command as ExportCmd


def test_export_default():

    output = StringIO()
    call_command(ExportCmd(), stdout=output)
    json.loads(output.getvalue())  # if no exception, then OK
    assert len(output.getvalue().splitlines()) == 1


def test_export_indent():
    output = StringIO()
    call_command(ExportCmd(), indent=1, stdout=output)
    assert len(output.getvalue().splitlines()) > 1


def test_export_to_file():
    with tempfile.TemporaryDirectory() as tmp:
        output_file = os.path.join(tmp, "result.json")
        call_command(ExportCmd(), output=output_file)
        with open(output_file, "r") as f:
            json.loads(f.read())


def test_export_custom():
    with pytest.raises(CommandError):
        call_command(ExportCmd(), api="something.that.doesnotexist")

    with pytest.raises(CommandError) as e:
        call_command(ExportCmd(), api="django.core.management.base.BaseCommand")
    assert (
        str(e.value)
        == "django.core.management.base.BaseCommand is not instance of NinjaAPI!"
    )

    call_command(ExportCmd(), api="demo.urls.api_v1")
    call_command(ExportCmd(), api="demo.urls.api_v2")
