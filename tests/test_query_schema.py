import sys
from datetime import datetime
from enum import IntEnum
from typing import Optional

import pytest
from pydantic import BaseModel, Field

from ninja import Form, Header, NinjaAPI, Query, Schema
from ninja.testing.client import TestClient

PY_310 = sys.version_info >= (3, 10)


class Range(IntEnum):
    TWENTY = 20
    FIFTY = 50
    TWO_HUNDRED = 200


class Filter(BaseModel):
    to_datetime: datetime = Field(alias="to")
    from_datetime: datetime = Field(alias="from")
    range: Range = Range.TWENTY


class Data(Schema):
    an_int: int = Field(alias="int", default=0)
    a_float: float = Field(alias="float", default=1.5)


api = NinjaAPI()


@api.get("/test")
def query_params_schema(request, filters: Filter = Query(...)):
    return filters.model_dump()


@api.get("/test-mixed")
def query_params_mixed_schema(
    request,
    query1: int,
    query2: int = 5,
    filters: Filter = Query(...),
    data: Data = Query(...),
):
    return dict(
        query1=query1,
        query2=query2,
        filters=filters.model_dump(),
        data=data.model_dump(),
    )


def test_request():
    client = TestClient(api)
    response = client.get("/test?from=1&to=2&range=20&foo=1&range2=50")
    print("!", response.json())
    assert response.json() == {
        "to_datetime": "1970-01-01T00:00:02Z",
        "from_datetime": "1970-01-01T00:00:01Z",
        "range": 20,
    }

    response = client.get("/test?from=1&to=2&range=21")
    assert response.status_code == 422


def test_request_mixed():
    client = TestClient(api)
    response = client.get(
        "/test-mixed?from=1&to=2&range=20&foo=1&range2=50&query1=2&int=3&float=1.6"
    )
    print(response.json())
    assert response.json() == {
        "data": {"a_float": 1.6, "an_int": 3},
        "filters": {
            "from_datetime": "1970-01-01T00:00:01Z",
            "range": 20,
            "to_datetime": "1970-01-01T00:00:02Z",
        },
        "query1": 2,
        "query2": 5,
    }

    response = client.get(
        "/test-mixed?from=1&to=2&range=20&foo=1&range2=50&query1=2&query2=10"
    )
    print(response.json())
    assert response.json() == {
        "data": {"a_float": 1.5, "an_int": 0},
        "filters": {
            "from_datetime": "1970-01-01T00:00:01Z",
            "range": 20,
            "to_datetime": "1970-01-01T00:00:02Z",
        },
        "query1": 2,
        "query2": 10,
    }

    response = client.get("/test-mixed?from=1&to=2")
    assert response.status_code == 422


def test_request_query_params_using_basemodel():
    class Foo(BaseModel):
        start: int
        optional: int = 42

    temp_api = NinjaAPI()

    @temp_api.get("/foo")
    def view(request, foo: Foo = Query(...)):
        return foo.model_dump()

    client = TestClient(temp_api)
    resp = client.get("/foo?start=1")

    assert resp.status_code == 200
    assert resp.json() == {"start": 1, "optional": 42}


def test_schema():
    schema = api.get_openapi_schema()
    params = schema["paths"]["/api/test"]["get"]["parameters"]
    print(params)
    assert params == [
        {
            "in": "query",
            "name": "to",
            "schema": {"format": "date-time", "title": "To", "type": "string"},
            "required": True,
        },
        {
            "in": "query",
            "name": "from",
            "schema": {"format": "date-time", "title": "From", "type": "string"},
            "required": True,
        },
        {
            "in": "query",
            "name": "range",
            "schema": {
                "allOf": [{"enum": [20, 50, 200], "title": "Range", "type": "integer"}],
                "default": 20,
            },
            "required": False,
        },
    ]


def test_schema_all_of_no_ref():
    details = {
        "default": 1,
        "allOf": [
            {"$ref": "#/components/schemas/Type"},
            {"no-ref-here": "xyzzy"},
        ],
    }
    definitions = {"Type": {"title": "Best Type Ever!"}}

    from ninja.openapi.schema import resolve_allOf

    resolve_allOf(details, definitions)

    assert details == {
        "default": 1,
        "allOf": [{"title": "Best Type Ever!"}, {"no-ref-here": "xyzzy"}],
    }


@pytest.mark.skipif(not PY_310, reason="requires Python 3.10+ pipe syntax")
def test_unwrap_union_model_no_model():
    """_unwrap_union_model returns input as-is when union has no pydantic model."""
    from ninja.signature.details import _unwrap_union_model

    annotation = int | None
    assert _unwrap_union_model(annotation) is annotation
    assert _unwrap_union_model(str) is str


def test_optional_query_schema():
    """Optional[Model] in Query should not crash (issue #1634)."""

    class MyFilter(Schema):
        name: str = "default"

    temp_api = NinjaAPI()

    @temp_api.get("/opt")
    def view(request, f: Optional[MyFilter] = Query(None)):
        if f:
            return f.model_dump()
        return {}

    client = TestClient(temp_api)

    resp = client.get("/opt?name=hello")
    assert resp.status_code == 200
    assert resp.json() == {"name": "hello"}

    resp = client.get("/opt")
    assert resp.status_code == 200


@pytest.mark.skipif(not PY_310, reason="requires Python 3.10+ pipe syntax")
def test_union_pipe_syntax_query_schema():
    """Model | None in Query should not crash (issue #1634, Python 3.10+ pipe syntax)."""

    class MyFilter(Schema):
        name: str = "default"

    temp_api = NinjaAPI()

    @temp_api.get("/pipe")
    def view(request, f: MyFilter | None = Query(None)):
        if f:
            return f.model_dump()
        return {}

    client = TestClient(temp_api)

    resp = client.get("/pipe?name=world")
    assert resp.status_code == 200
    assert resp.json() == {"name": "world"}

    resp = client.get("/pipe")
    assert resp.status_code == 200


@pytest.mark.skipif(not PY_310, reason="requires Python 3.10+ pipe syntax")
def test_nested_optional_query_schema():
    """Nested optional model fields should also work."""

    class Inner(Schema):
        value: Optional[int] = 0
        items: list[str] = []

    class Outer(Schema):
        inner: Inner | None = None
        label: str = "x"

    temp_api = NinjaAPI()

    @temp_api.get("/nested")
    def view(request, f: Outer = Query(...)):
        return f.model_dump()

    client = TestClient(temp_api)

    resp = client.get("/nested?label=test")
    assert resp.status_code == 200
    assert resp.json()["label"] == "test"


def test_optional_query_schema_not_sent_uses_default():
    """Optional[Model] = Query(None) falls back to None when no field is sent (issue #1805)."""

    class Required(Schema):
        x: int

    class AllOptional(Schema):
        a: Optional[int] = None

    temp_api = NinjaAPI()

    @temp_api.get("/required")
    def required(request, f: Optional[Required] = Query(None)):
        return {"f": f.model_dump() if f else None}

    @temp_api.get("/all-optional")
    def all_optional(request, f: Optional[AllOptional] = Query(None)):
        return {"f": f.model_dump() if f else None}

    client = TestClient(temp_api)

    resp = client.get("/required")
    assert resp.status_code == 200
    assert resp.json() == {"f": None}

    resp = client.get("/required?x=1")
    assert resp.json() == {"f": {"x": 1}}

    resp = client.get("/all-optional")
    assert resp.status_code == 200
    assert resp.json() == {"f": None}

    resp = client.get("/all-optional?a=2")
    assert resp.json() == {"f": {"a": 2}}


def test_required_nested_query_schema_keeps_defaults_and_loc():
    """Required nested models are still built from defaults and report the field loc."""

    class Inner(Schema):
        y: Optional[int] = None

    class Outer(Schema):
        i: Inner
        z: Optional[int] = None

    class Strict(Schema):
        x: int

    class Outer2(Schema):
        s: Strict

    temp_api = NinjaAPI()

    @temp_api.get("/c")
    def c(request, f: Outer = Query(...)):
        return f.model_dump()

    @temp_api.get("/o")
    def o(request, f: Optional[Outer] = Query(None)):
        return f.model_dump() if f else None

    @temp_api.get("/s")
    def s(request, f: Outer2 = Query(...)):
        return f.model_dump()

    client = TestClient(temp_api)

    assert client.get("/c").json() == {"i": {"y": None}, "z": None}
    assert client.get("/c?z=1").json() == {"i": {"y": None}, "z": 1}
    assert client.get("/o").json() is None
    assert client.get("/o?z=1").json() == {"i": {"y": None}, "z": 1}
    resp = client.get("/s")
    assert resp.status_code == 422
    assert resp.json()["detail"][0]["loc"][-1] == "x"


def test_optional_schema_default_only_when_annotation_allows_none():
    class Required(Schema):
        x: int

    class AllOptional(Schema):
        a: Optional[int] = None

    temp_api = NinjaAPI()

    @temp_api.get("/header")
    def header(request, f: Optional[Required] = Header(None)):
        return f and f.model_dump()

    @temp_api.post("/form")
    def form(request, f: Optional[Required] = Form(None)):
        return f and f.model_dump()

    @temp_api.get("/other-param")
    def other_param(request, q: int = 0, f: Optional[Required] = Query(None)):
        return {"q": q, "f": f and f.model_dump()}

    @temp_api.get("/not-optional")
    def not_optional(request, f: AllOptional = Query(None)):
        return f.model_dump()

    @temp_api.get("/instance-default")
    def instance_default(request, f: Optional[AllOptional] = Query(AllOptional(a=5))):
        return f.model_dump()

    client = TestClient(temp_api)

    assert client.get("/header").json() is None
    assert client.get("/header", headers={"x": "1"}).json() == {"x": 1}
    assert client.post("/form").json() is None
    assert client.post("/form", POST={"x": "1"}).json() == {"x": 1}
    assert client.get("/other-param?q=3").json() == {"q": 3, "f": None}
    # without Optional the schema is still built from its field defaults
    assert client.get("/not-optional").json() == {"a": None}
    assert client.get("/instance-default").json() == {"a": 5}
    assert client.get("/instance-default?a=1").json() == {"a": 1}


def test_optional_query_schema_openapi_params():
    class Filters(Schema):
        x: int
        y: Optional[str] = None

    class Order(IntEnum):
        ASC = 1
        DESC = 2

    temp_api = NinjaAPI()

    @temp_api.get("/optional")
    def optional(
        request, f: Optional[Filters] = Query(None), order: Optional[Order] = None
    ):
        pass

    @temp_api.get("/required")
    def required(request, f: Filters = Query(...)):
        pass

    paths = temp_api.get_openapi_schema()["paths"]

    def params(path):
        return {p["name"]: p["required"] for p in paths[path]["get"]["parameters"]}

    assert params("/api/optional") == {"x": False, "y": False, "order": False}
    assert params("/api/required") == {"x": True, "y": False}
