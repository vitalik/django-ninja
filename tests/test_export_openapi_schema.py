import json
import sys
from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from ninja.responses import NinjaJSONEncoder
from ninja.yaml import NinjaSafeDumper, yaml


@pytest.fixture
def call_cmd():
    def inner(**kwargs):
        stdout = StringIO()
        call_command("export_openapi_schema", stdout=stdout, **kwargs)
        return stdout.getvalue()

    return inner


@pytest.mark.parametrize(
    "fmt,is_ok",
    (
        ("json", json.loads),
        ("yaml", yaml.safe_load),
        ("foobarbaz", id),
    ),
)
def test_export_default(fmt, is_ok, call_cmd):
    output = call_cmd(format=fmt)
    assert is_ok(output)  # if no exception, then OK


@pytest.mark.parametrize("sort_keys", (None, False, True))
def test_export_json_sort_keys(sort_keys, mocker, call_cmd):
    encoder = mocker.spy(NinjaJSONEncoder, "__init__")
    output = call_cmd(format="json", sort_keys=sort_keys)
    assert encoder.call_args[1]["sort_keys"] is sort_keys
    if sort_keys:
        data = json.loads(output)
        assert [*data.keys()] == sorted(data.keys())


@pytest.mark.parametrize("sort_keys", (None, False, True))
def test_export_yaml_sort_keys(sort_keys, mocker, call_cmd):
    dumper = mocker.spy(NinjaSafeDumper, "__init__")
    output = call_cmd(format="yaml", sort_keys=sort_keys)
    assert dumper.call_args[1]["sort_keys"] is sort_keys
    if sort_keys:
        data = yaml.safe_load(output)
        assert [*data.keys()] == sorted(data.keys())


def test_export_indent(call_cmd):
    output = call_cmd(indent=1)
    assert len(output.splitlines()) > 1


def test_export_to_file(tmp_path, call_cmd):
    output_file = tmp_path / "result.json"
    stdout = call_cmd(output=output_file)
    parsed_file = json.loads(output_file.read_text())
    assert len(stdout) == 0
    assert type(parsed_file) is dict


def test_export_custom(call_cmd):
    with pytest.raises(CommandError):
        call_cmd(api="something.that.doesnotexist")

    with pytest.raises(CommandError, match="not instance of NinjaAPI"):
        call_cmd(api="django.core.management.base.BaseCommand")

    call_cmd(api="demo.urls.api_v1")
    call_cmd(api="demo.urls.api_v2")


def test_export_yaml_json_equivalent(call_cmd):
    yaml_output = call_cmd(format="yaml")
    yaml_data = yaml.load(yaml_output, Loader=yaml.SafeLoader)

    json_output = call_cmd(format="json")
    json_data = json.loads(json_output)

    # in json, keys can only be strings. in yaml, keys can be other types, or
    # even complex objects. therefore, the python dict {200: 'OK'} will be
    # represented as {"200": "OK"} in json, and as {200: OK} in yaml. when
    # deserializing these representations, the resulting python dicts will have
    # different key types: string vs. int.
    # this function serializes the keys of a given dict in order to fairly
    # compare json output to yaml output.
    def serialize_keys(val):
        if type(val) == dict:
            return {str(k): serialize_keys(v) for k, v in val.items()}
        return val

    assert serialize_keys(yaml_data) == json_data


def test_export_yaml_missing_package(call_cmd, monkeypatch):
    monkeypatch.syspath_prepend("tests/mock")
    del sys.modules["yaml"]
    del sys.modules["ninja.yaml"]
    with pytest.raises(ModuleNotFoundError, match="PyYAML"):
        call_cmd(format="yaml")
