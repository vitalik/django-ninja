import json
from pathlib import Path

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client as DjangoTestClient

from ninja.testing import TestClient as NinjaTestClient
from tests.demo_project.multi_param.api import router

ninja_client = NinjaTestClient(router)

test_file = SimpleUploadedFile("test.txt", b"data123")

expected_response = {
    "i": 1,
    "s": "a-str",
    "data": {"foo4": 44, "bar4": "44bar"},
    "nested-data": {
        "foo": 11,
        "bar": "11bar",
        "d2": {"foo2": 22, "bar2": "22bar", "d3": {"foo3": 33, "bar3": "33bar"}},
    },
}

test_client_args = {
    "/test-multi-query": {
        "query": "i=1&s=a-str&foo4=44&bar4=44bar&foo=11&bar=11bar&foo2=22&bar2=22bar&foo3=33&bar3=33bar",
    },
    "/test-multi-path/{i}/{s}/{foo4}/{bar4}/{foo}/{bar}/{foo2}/{bar2}/{foo3}/{bar3}/": {
        "path": "/test-multi-path/1/a-str/44/44bar/11/11bar/22/22bar/33/33bar/"
    },
    "/test-multi-header": {"headers": {"i": 1, "foo": 11, "bar2": "22bar", "foo3": 33}},
    "/test-multi-cookie": {"COOKIES": {"i": 1, "foo": 11, "bar2": "22bar", "foo3": 33}},
    "/test-multi-form": {"POST": {"i": 1, "foo": 11, "bar2": "22bar", "foo3": 33}},
    "/test-multi-body": {"json": expected_response},
    "/test-multi-body-file": {
        "FILES": {"file": test_file},
        "POST": {
            k: json.dumps(v) if isinstance(v, dict) else str(v)
            for k, v in expected_response.items()
        },
    },
    "/test-multi-form-file": {
        "FILES": {"file": test_file},
        "POST": {"i": 1, "foo": 11, "bar2": "22bar", "foo3": 33},
    },
    "/test-multi-body-form": {
        "POST": {
            "i": "1",
            "foo": 11,
            "bar2": "22bar",
            "foo3": 33,
            "data": '{"foo4": 44, "bar4": "44bar"}',
        }
    },
    "/test-multi-form-body": {
        "POST": {
            "i": 1,
            "nested-data": '{"foo": 11, "d2": {"bar2": "22bar", "d3": {"foo3": 33}}}',
        }
    },
    "/test-multi-body-form-file": {
        "FILES": {"file": test_file},
        "POST": {
            "i": "1",
            "foo": 11,
            "bar2": "22bar",
            "foo3": 33,
            "data": '{"foo4": 44, "bar4": "44bar"}',
        },
    },
    "/test-multi-form-body-file": {
        "FILES": {"file": test_file},
        "POST": {
            "i": 1,
            "nested-data": '{"foo": 11, "d2": {"bar2": "22bar", "d3": {"foo3": 33}}}',
        },
    },
}


def test_validate_test_data():
    ops = router.path_operations
    schema = DjangoTestClient().get("/api/mp/openapi.json").json()

    for path in tuple(schema["paths"]):
        schema["paths"]["/" + path.split("/", 3)[3]] = schema["paths"].pop(path)
    assert set(ops) == set(
        schema["paths"]
    ), "Expect a test case for each endpoint on the API"

    fixture_dir = Path(__file__).parent / "schema_fixtures"
    fixture_files = {
        path: (fixture_dir / f"{path.split('/', 2)[1]}.json") for path in ops
    }

    # verify that the currently generated schema matches the fixtures.  Since the generated
    # schema is in git, this allows any changes in behavior to be documented over time.
    for path, filename in fixture_files.items():
        if 0:  # pragma: nocover
            # if test cases or schema generation changes,
            #   use this block of code to regenerate the fixtures
            with open(filename, "w") as f:
                json.dump(schema["paths"][path], f, indent=2)
        with open(filename) as f:
            data = json.load(f)
            assert json.loads(json.dumps(schema["paths"][path])) == data


@pytest.mark.parametrize("path, client_args", tuple(test_client_args.items()))
def test_data_round_trip_with_ninja_client(path, client_args):
    client_args = test_client_args[path]
    kwargs = {"path": path}
    for k in ("path", "headers", "COOKIES", "POST", "json", "FILES"):
        if k in client_args:
            kwargs[k] = client_args[k]

    query = client_args.get("query")
    if query:
        kwargs["path"] += f"?{query}"

    response = ninja_client.post(**kwargs)
    assert response.json() == expected_response
    assert response.status_code == 200


@pytest.mark.parametrize("path, client_args", tuple(test_client_args.items()))
def test_data_round_trip_with_django_client(path, client_args):
    django_client = DjangoTestClient()

    client_args = test_client_args[path]
    kwargs = {"path": client_args.get("path", path)}

    if "headers" in client_args:
        for k, v in client_args["headers"].items():
            kwargs[f"HTTP_{k.upper()}"] = v

    if "COOKIES" in client_args:
        django_client.cookies.load(client_args["COOKIES"])

    if "POST" in client_args:
        kwargs["data"] = client_args["POST"]

    if "FILES" in client_args:
        if "data" in kwargs:
            kwargs["data"].update(client_args["FILES"])
        else:
            kwargs["data"] = client_args["FILES"]

    if "json" in client_args:
        assert "data" not in kwargs
        kwargs["data"] = json.dumps(client_args["json"])
        kwargs["content_type"] = "application/json"

    query = client_args.get("query")
    if query:
        kwargs["path"] += f"?{query}"

    kwargs["path"] = "/api/mp" + kwargs["path"]

    response = django_client.post(**kwargs)
    assert response.json() == expected_response
    assert response.status_code == 200
