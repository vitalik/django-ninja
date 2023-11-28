import json
import tempfile
from io import StringIO
from pathlib import Path
from unittest.mock import patch

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
        output_file = Path(tmp) / "result.json"
        call_command(ExportCmd(), output=output_file)
        json.loads(Path(output_file).read_text())


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


@patch("ninja.management.commands.export_openapi_schema.resolve")
def test_export_default_without_api_endpoint(mock):
    mock.side_effect = AttributeError()
    output = StringIO()
    with pytest.raises(CommandError) as e:
        call_command(ExportCmd(), stdout=output)
    assert str(e.value) == "No NinjaAPI instance found; please specify one with --api"
