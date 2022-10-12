from collections import OrderedDict
from decimal import Decimal

import pytest
import yaml
from pydantic import BaseModel

from ninja import NinjaAPI, Router
from ninja.openapi.schema import OpenAPISchema
from ninja.yaml import NinjaSafeDumper


@pytest.fixture
def dump_yaml():
    def inner(value):
        return yaml.dump(value, Dumper=NinjaSafeDumper)

    return inner


@pytest.fixture
def api_schema():
    router = Router()
    api = NinjaAPI(title="YAML testing!")

    class SomeSchema(BaseModel):
        pass

    @router.get("yaml-path", response={200: SomeSchema})
    def yaml_path(request, foobar: int) -> SomeSchema:
        pass

    api.add_router("/yaml-router", router)
    return OpenAPISchema(api, path_prefix="/yaml-test")


def test_yaml_dump_decimal(dump_yaml):
    output = dump_yaml(Decimal(1) / Decimal(7))
    assert output == f"'{Decimal(1) / Decimal(7)}'\n"


def test_yaml_dump_ordered_dict(dump_yaml):
    output = dump_yaml(OrderedDict([(1, "foo"), (2, "bar")]))
    assert (
        output
        == "1: foo\n2: bar\n"
    )


def test_yaml_dump_openapi_schema(dump_yaml, api_schema):
    output = yaml.dump(api_schema, Dumper=NinjaSafeDumper)
    expected = """components:
  schemas:
    SomeSchema:
      properties: {}
      title: SomeSchema
      type: object
info:
  description: ''
  title: YAML testing!
  version: 1.0.0
openapi: 3.0.2
paths:
  /yaml-test/yaml-router/yaml-path:
    get:
      operationId: test_yaml_yaml_path
      parameters:
      - in: query
        name: foobar
        required: true
        schema:
          title: Foobar
          type: integer
      responses:
        200:
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/SomeSchema'
          description: OK
      summary: Yaml Path
"""
    assert output == expected
