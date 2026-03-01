import json

import pytest
from django.http import HttpResponse

from ninja import NinjaAPI, Schema
from ninja.streaming import JSONL, SSE, StreamFormat
from ninja.testing import TestAsyncClient, TestClient


class Item(Schema):
    name: str
    price: float = 0.0


# --- Sync JSONL ---

api = NinjaAPI()


@api.get("/jsonl/items", response=JSONL[Item])
def jsonl_items(request):
    for i in range(3):
        yield {"name": f"item-{i}", "price": float(i)}


@api.get("/sse/items", response=SSE[Item])
def sse_items(request):
    for i in range(3):
        yield {"name": f"item-{i}", "price": float(i)}


@api.post("/jsonl/echo", response=JSONL[Item])
def jsonl_echo(request):
    yield {"name": "posted", "price": 1.0}


@api.get("/jsonl/with-params/{item_id}", response=JSONL[Item])
def jsonl_with_params(request, item_id: int, q: str = "default"):
    yield {"name": f"item-{item_id}-{q}", "price": 0.0}


@api.get("/jsonl/with-headers", response=JSONL[Item])
def jsonl_with_headers(request, response: HttpResponse):
    response["X-Custom"] = "hello"
    response.set_cookie("session", "abc123")
    yield {"name": "with-headers", "price": 0.0}


client = TestClient(api)


class TestJSONLSync:
    def test_jsonl_basic(self):
        response = client.get("/jsonl/items")
        assert response.status_code == 200
        assert response["Content-Type"] == "application/jsonl"
        lines = response.content.decode().strip().split("\n")
        assert len(lines) == 3
        for i, line in enumerate(lines):
            data = json.loads(line)
            assert data == {"name": f"item-{i}", "price": float(i)}

    def test_jsonl_validates_schema(self):
        """Each item is validated through Pydantic schema."""
        response = client.get("/jsonl/items")
        lines = response.content.decode().strip().split("\n")
        for line in lines:
            data = json.loads(line)
            # Should have both fields (price has default)
            assert "name" in data
            assert "price" in data


class TestSSESync:
    def test_sse_basic(self):
        response = client.get("/sse/items")
        assert response.status_code == 200
        assert response["Content-Type"] == "text/event-stream"
        content = response.content.decode()
        events = content.strip().split("\n\n")
        assert len(events) == 3
        for i, event in enumerate(events):
            assert event.startswith("data: ")
            data = json.loads(event[len("data: ") :])
            assert data == {"name": f"item-{i}", "price": float(i)}

    def test_sse_headers(self):
        response = client.get("/sse/items")
        assert response["Cache-Control"] == "no-cache"
        assert response["X-Accel-Buffering"] == "no"


class TestPostStreaming:
    def test_post_jsonl(self):
        response = client.post("/jsonl/echo")
        assert response.status_code == 200
        lines = response.content.decode().strip().split("\n")
        assert len(lines) == 1
        assert json.loads(lines[0]) == {"name": "posted", "price": 1.0}


class TestStreamingWithParams:
    def test_path_and_query_params(self):
        response = client.get("/jsonl/with-params/42?q=test")
        assert response.status_code == 200
        lines = response.content.decode().strip().split("\n")
        assert json.loads(lines[0]) == {"name": "item-42-test", "price": 0.0}


class TestStreamingHeaders:
    def test_temporal_response_headers(self):
        response = client.get("/jsonl/with-headers")
        assert response.status_code == 200
        assert response["X-Custom"] == "hello"
        assert "session" in response.cookies


# --- Async ---

async_api = NinjaAPI()


@async_api.get("/jsonl/items", response=JSONL[Item])
async def async_jsonl_items(request):
    for i in range(3):
        yield {"name": f"item-{i}", "price": float(i)}


@async_api.get("/sse/items", response=SSE[Item])
async def async_sse_items(request):
    for i in range(3):
        yield {"name": f"item-{i}", "price": float(i)}


async_client = TestAsyncClient(async_api)


@pytest.mark.asyncio
class TestAsyncJSONL:
    async def test_async_jsonl(self):
        response = await async_client.get("/jsonl/items")
        assert response.status_code == 200
        assert response["Content-Type"] == "application/jsonl"
        lines = response.content.decode().strip().split("\n")
        assert len(lines) == 3
        for i, line in enumerate(lines):
            data = json.loads(line)
            assert data == {"name": f"item-{i}", "price": float(i)}


@pytest.mark.asyncio
class TestAsyncSSE:
    async def test_async_sse(self):
        response = await async_client.get("/sse/items")
        assert response.status_code == 200
        assert response["Content-Type"] == "text/event-stream"
        assert response["Cache-Control"] == "no-cache"
        content = response.content.decode()
        events = content.strip().split("\n\n")
        assert len(events) == 3


# --- OpenAPI Schema ---


class TestOpenAPISchema:
    def test_jsonl_openapi(self):
        schema = api.get_openapi_schema()
        path = schema["paths"]["/api/jsonl/items"]["get"]
        resp = path["responses"][200]
        assert "application/jsonl" in resp["content"]
        item_schema = resp["content"]["application/jsonl"]["schema"]
        # Should reference the Item schema
        assert item_schema.get("$ref") or item_schema.get("properties")

    def test_sse_openapi(self):
        schema = api.get_openapi_schema()
        path = schema["paths"]["/api/sse/items"]["get"]
        resp = path["responses"][200]
        assert "text/event-stream" in resp["content"]
        sse_schema = resp["content"]["text/event-stream"]["schema"]
        assert sse_schema["type"] == "object"
        assert "data" in sse_schema["properties"]


# --- Custom StreamFormat ---


class NDJSON(StreamFormat):
    media_type = "application/x-ndjson"

    @classmethod
    def format_chunk(cls, data: str) -> str:
        return data + "\n"


custom_api = NinjaAPI()


@custom_api.get("/ndjson/items", response=NDJSON[Item])
def ndjson_items(request):
    for i in range(2):
        yield {"name": f"item-{i}", "price": float(i)}


custom_client = TestClient(custom_api)


class TestCustomFormat:
    def test_custom_ndjson(self):
        response = custom_client.get("/ndjson/items")
        assert response.status_code == 200
        assert response["Content-Type"] == "application/x-ndjson"
        lines = response.content.decode().strip().split("\n")
        assert len(lines) == 2

    def test_custom_openapi(self):
        schema = custom_api.get_openapi_schema()
        path = schema["paths"]["/api/ndjson/items"]["get"]
        resp = path["responses"][200]
        assert "application/x-ndjson" in resp["content"]


# --- Multiple methods ---

multi_api = NinjaAPI()


@multi_api.patch("/patch-stream", response=JSONL[Item])
def patch_stream(request):
    yield {"name": "patched", "price": 0.0}


@multi_api.put("/put-stream", response=JSONL[Item])
def put_stream(request):
    yield {"name": "put", "price": 0.0}


@multi_api.delete("/delete-stream", response=JSONL[Item])
def delete_stream(request):
    yield {"name": "deleted", "price": 0.0}


multi_client = TestClient(multi_api)


class TestMultipleMethods:
    def test_patch_stream(self):
        response = multi_client.patch("/patch-stream")
        assert response.status_code == 200
        assert json.loads(response.content.decode().strip()) == {
            "name": "patched",
            "price": 0.0,
        }

    def test_put_stream(self):
        response = multi_client.put("/put-stream")
        assert response.status_code == 200
        assert json.loads(response.content.decode().strip()) == {
            "name": "put",
            "price": 0.0,
        }

    def test_delete_stream(self):
        response = multi_client.delete("/delete-stream")
        assert response.status_code == 200
        assert json.loads(response.content.decode().strip()) == {
            "name": "deleted",
            "price": 0.0,
        }
