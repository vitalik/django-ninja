from types import SimpleNamespace
from typing import Optional

from ninja import Field, NinjaAPI, Schema
from ninja.testing import TestClient


class SchemaWithAlias(Schema):
    foo: str = Field("", alias="bar")


api = NinjaAPI()


@api.get("/path", response=SchemaWithAlias)
def alias_operation(request):
    return {"bar": "value"}


def test_alias():
    schema = api.get_openapi_schema()["components"]
    print(schema)
    assert schema == {
        "schemas": {
            "SchemaWithAlias": {
                "type": "object",
                "properties": {
                    "foo": {"type": "string", "default": "", "title": "Foo"}
                },
                "title": "SchemaWithAlias",
            }
        }
    }


# TODO: check the conflicting approach
#       when alias is used both for response and request schema
#       basically it need to generate 2 schemas - one with alias another without
# @api.post("/path", response=SchemaWithAlias)
# def alias_operation(request, payload: SchemaWithAlias):
#     return {"bar": payload.foo}

# ---------------------------------------------------------------------------
# Numeric aliases (e.g. alias="0") used to break validation from objects:
# DjangoGetter resolved the alias through django's template Variable, which
# parses "0" as a numeric literal and returned the number itself instead of
# the attribute, so every field under a numeric alias silently became None.
# ---------------------------------------------------------------------------


class ShiftSchema(Schema):
    start: Optional[str] = None
    end: Optional[str] = None


class DaySchema(Schema):
    first: ShiftSchema = Field(None, alias="0")
    second: ShiftSchema = Field(None, alias="1")

    model_config = {"populate_by_name": True}


class WeekSchema(Schema):
    mon: DaySchema = Field(None, alias="0")
    tue: DaySchema = Field(None, alias="1")

    model_config = {"populate_by_name": True}


def make_week() -> WeekSchema:
    day = DaySchema()
    day.first = ShiftSchema(start="09:00", end="17:00")
    week = WeekSchema()
    week.mon = day
    return week


def test_numeric_alias_model_validate_from_instance():
    result = WeekSchema.model_validate(make_week())
    assert result.model_dump(by_alias=True)["0"]["0"] == {
        "start": "09:00",
        "end": "17:00",
    }


def test_numeric_alias_model_validate_from_object():
    day = SimpleNamespace(
        first=SimpleNamespace(start="08:00", end="12:00"), second=None
    )
    result = DaySchema.model_validate(day)
    assert result.model_dump(by_alias=True)["0"] == {
        "start": "08:00",
        "end": "12:00",
    }


def test_numeric_alias_model_validate_from_dict():
    result = WeekSchema.model_validate({"0": {"0": {"start": "07:00", "end": "11:00"}}})
    assert result.model_dump(by_alias=True)["0"]["0"] == {
        "start": "07:00",
        "end": "11:00",
    }


def test_numeric_alias_populate_by_name_dump():
    week = WeekSchema(mon=DaySchema(first=ShiftSchema(start="06:00", end="10:00")))
    result = WeekSchema.model_validate(week)
    assert result.model_dump(by_alias=True)["0"]["0"]["start"] == "06:00"


numeric_api = NinjaAPI(urls_namespace="numeric_alias")


@numeric_api.get("/week", response=WeekSchema, by_alias=True)
def week_operation(request):
    return make_week()


def test_numeric_alias_response_values_are_not_nulled():
    response = TestClient(numeric_api).get("/week")
    assert response.status_code == 200
    assert response.json()["0"]["0"] == {"start": "09:00", "end": "17:00"}
