from io import StringIO
import pytest
import json

from django.core.management.base import CommandError
from django.core.management import call_command
from ninja.management.commands import export_openapi_schema
from ninja import Field, NinjaAPI, Schema
from ninja.responses import NinjaJSONEncoder


api = NinjaAPI()


class CustomAPI(NinjaAPI):
    pass


custom_api = CustomAPI()

non_ninja_api_attr = object()


class VersionSchema(Schema):
    version: str


@custom_api.get(
    "/version",
    response=VersionSchema,
    operation_id="test_export_openapi_schema",
)
@api.get(
    "/version",
    response=VersionSchema,
    operation_id="test_export_openapi_schema",
)
def get_version(request):
    return {"version": "1.0.0"}


@pytest.mark.parametrize("api_attr", (("api"), ("custom_api")))
def test_export_openapi_schema_stdout(api_attr):
    out = StringIO()

    call_command(
        export_openapi_schema.Command(),
        api=f"tests.test_export_openapi_schema.{api_attr}",
        stdout=out,
    )

    schema = json.dumps(api.get_openapi_schema(), cls=NinjaJSONEncoder) + "\n"

    assert out.getvalue() == schema


def test_export_openapi_schema_file(tmp_path):
    output_file = tmp_path / "openapi.json"

    call_command(
        export_openapi_schema.Command(),
        api="tests.test_export_openapi_schema.api",
        output=str(output_file),
    )

    schema = json.dumps(api.get_openapi_schema(), cls=NinjaJSONEncoder)

    assert output_file.read_text() == schema


def test_path_depth_less_than_two():
    with pytest.raises(CommandError) as e:
        call_command(
            export_openapi_schema.Command(),
            api="one_depth_api",
        )

    assert (
        str(e.value)
        == "Module should contains at least package and api instance name attribute!"
    )


def test_no_module():
    with pytest.raises(CommandError) as e:
        call_command(
            export_openapi_schema.Command(),
            api="fake_module_123.api",
        )

    assert str(e.value) == "Module fake_module_123 not found!"


def test_no_app_in_module():
    with pytest.raises(CommandError) as e:
        call_command(
            export_openapi_schema.Command(),
            api="tests.test_export_openapi_schema.api_123",
        )

    assert (
        str(e.value)
        == "Module 'tests.test_export_openapi_schema' has no attribute 'api_123'"
    )


def test_non_ninja_api_app():
    module_path = "tests.test_export_openapi_schema.non_ninja_api_attr"

    with pytest.raises(CommandError) as e:
        call_command(
            export_openapi_schema.Command(),
            api=module_path,
        )

    assert str(e.value) == f"{module_path} is not instance of NinjaAPI!"


# TODO: YML parser and schema export?
