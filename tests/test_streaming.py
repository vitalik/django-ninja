import asyncio
import json

import django
import pytest
from asgiref.testing import ApplicationCommunicator
from django.core.exceptions import PermissionDenied
from django.core.handlers.asgi import ASGIHandler
from django.http import HttpResponse
from django.test import RequestFactory, override_settings
from django.urls import path, resolve
from pydantic import ValidationError

from ninja import NinjaAPI, Schema
from ninja.compatibility.streaming import create_streaming_response
from ninja.errors import AuthorizationError, HttpError
from ninja.operation import AsyncOperation
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


@async_api.get("/jsonl/with-headers", response=JSONL[Item])
async def async_jsonl_with_headers(request, response: HttpResponse):
    response["X-Custom"] = "async-hello"
    response.set_cookie("token", "xyz")
    yield {"name": "async-headers", "price": 0.0}


async_client = TestAsyncClient(async_api)


@pytest.mark.asyncio
@pytest.mark.parametrize("stream_format", [SSE, JSONL])
@pytest.mark.parametrize("error", [AuthorizationError(), HttpError(403, "denied")])
async def test_async_stream_permission_denied(stream_format, error):
    api = NinjaAPI()

    @api.get("/", response=stream_format[Item])
    async def stream(request):
        raise error
        yield  # pragma: no cover

    response = await TestAsyncClient(api).get("/")
    assert response.status_code == 403
    assert not response.streaming
    assert response.json() == {"detail": str(error)}


@pytest.mark.asyncio
@pytest.mark.parametrize("invalid_item", [False, True])
async def test_async_stream_preparation_exception_handler(invalid_item):
    api = NinjaAPI()
    closed = []

    @api.exception_handler(ValidationError if invalid_item else ValueError)
    def handle_error(request, exc):
        return api.create_response(
            request, {"detail": "preparation failed"}, status=400
        )

    @api.get("/", response=JSONL[Item])
    async def stream(request):
        try:
            if not invalid_item:
                raise ValueError("failed")
            yield {"price": "invalid"}
        finally:
            closed.append(True)

    response = await TestAsyncClient(api).get("/")
    assert response.status_code == 400
    assert response.json() == {"detail": "preparation failed"}
    assert closed == [True]


@pytest.mark.asyncio
@pytest.mark.parametrize("empty", [False, True])
async def test_async_stream_preparation_headers(empty):
    api = NinjaAPI()

    @api.get("/", response=SSE[Item])
    async def stream(request, response: HttpResponse):
        response.status_code = 201
        response["X-Prepared"] = "yes"
        response["Content-Type"] = "text/plain"
        response.set_cookie("prepared", "yes")
        if not empty:
            yield {"name": "first"}

    urls = type("URLConf", (), {"urlpatterns": [path("", api.urls)]})
    with override_settings(
        ROOT_URLCONF=urls, MIDDLEWARE=[], ALLOWED_HOSTS=["testserver"]
    ):
        response = await resolve("/", urlconf=urls).func(RequestFactory().get("/"))
    assert response.status_code == 201
    assert response["X-Prepared"] == "yes"
    assert response["Content-Type"] == "text/event-stream"
    assert response["Cache-Control"] == "no-cache"
    assert response.cookies["prepared"].value == "yes"
    if django.VERSION >= (4, 2):
        chunks = [chunk async for chunk in response.streaming_content]
    else:
        chunks = list(response.streaming_content)
    assert len(chunks) == (0 if empty else 1)


@pytest.mark.asyncio
@pytest.mark.skipif(django.VERSION < (4, 2), reason="Requires native async streaming")
@pytest.mark.parametrize("ending", ["complete", "error", "cancel"])
async def test_async_stream_remains_lazy_and_closes(ending):
    api = NinjaAPI()
    events = []
    waiting = asyncio.Event()

    @api.get("/", response=JSONL[Item])
    async def stream(request):
        try:
            events.append("first")
            yield {"name": "first"}
            events.append("second")
            if ending == "error":
                raise HttpError(403, "late denial")
            if ending == "cancel":
                waiting.set()
                await asyncio.Event().wait()
            yield {"name": "second"}
        finally:
            events.append("closed")

    urls = type("URLConf", (), {"urlpatterns": [path("", api.urls)]})
    with override_settings(
        ROOT_URLCONF=urls, MIDDLEWARE=[], ALLOWED_HOSTS=["testserver"]
    ):
        response = await resolve("/", urlconf=urls).func(RequestFactory().get("/"))
    assert response.status_code == 200
    assert events == ["first"]
    content = response.streaming_content
    assert json.loads(await content.__anext__()) == {"name": "first", "price": 0.0}
    assert events == ["first"]
    if ending == "complete":
        assert json.loads(await content.__anext__()) == {"name": "second", "price": 0.0}
        with pytest.raises(StopAsyncIteration):
            await content.__anext__()
    elif ending == "error":
        with pytest.raises(HttpError):
            await content.__anext__()
    else:
        next_chunk = asyncio.create_task(content.__anext__())
        await asyncio.wait_for(waiting.wait(), timeout=1)
        next_chunk.cancel()
        with pytest.raises(asyncio.CancelledError):
            await next_chunk
    assert events == ["first", "second", "closed"]
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_async_stream_permission_denied_asgi():
    api = NinjaAPI()

    @api.get("/", response=SSE[Item])
    async def stream(request):
        raise PermissionDenied
        yield  # pragma: no cover

    urls = type("URLConf", (), {"urlpatterns": [path("", api.urls)]})
    with override_settings(
        ROOT_URLCONF=urls, DEBUG=False, MIDDLEWARE=[], ALLOWED_HOSTS=["testserver"]
    ):
        application = ApplicationCommunicator(
            ASGIHandler(),
            {
                "type": "http",
                "asgi": {"version": "3.0"},
                "http_version": "1.1",
                "method": "GET",
                "path": "/",
                "query_string": b"",
                "headers": [(b"host", b"testserver")],
            },
        )
        try:
            await application.send_input({"type": "http.request", "body": b""})
            start = await application.receive_output()
            assert start["type"] == "http.response.start"
            assert start["status"] == 403
            body = await application.receive_output()
            assert body["type"] == "http.response.body"
            assert body["body"]
            await application.wait()
        finally:
            application.stop()


@pytest.mark.asyncio
async def test_async_stream_response_accepts_async_iterator():
    class Items:
        def __init__(self):
            self.items = iter([{"name": "first"}, {"name": "second"}])

        def __aiter__(self):
            return self

        async def __anext__(self):
            try:
                return next(self.items)
            except StopIteration:
                raise StopAsyncIteration from None

    operation = AsyncOperation("/", ["GET"], lambda request: None, response=JSONL[Item])
    response = await operation._async_stream_response(
        RequestFactory().get("/"), Items(), HttpResponse()
    )
    if django.VERSION >= (4, 2):
        chunks = [chunk async for chunk in response.streaming_content]
    else:
        chunks = list(response.streaming_content)
    assert [json.loads(chunk)["name"] for chunk in chunks] == ["first", "second"]


@pytest.mark.asyncio
async def test_create_streaming_response_preserves_explicit_status():
    temporal_response = HttpResponse(status=200)
    events = []

    async def content():
        events.append("started")
        temporal_response.status_code = 201
        yield "first\n"
        temporal_response["X-Finished"] = "yes"

    response = await create_streaming_response(
        content(),
        content_type="application/jsonl",
        status=202,
        temporal_response=temporal_response,
        extra_headers={},
    )
    assert response.status_code == 202
    if django.VERSION >= (4, 2):
        assert events == []
        chunks = [chunk async for chunk in response.streaming_content]
    else:
        chunks = list(response.streaming_content)
    assert chunks == [b"first\n"]
    assert response.status_code == 202
    assert response["X-Finished"] == "yes"


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


@pytest.mark.asyncio
class TestAsyncHeaders:
    async def test_async_temporal_response_headers(self):
        response = await async_client.get("/jsonl/with-headers")
        assert response.status_code == 200
        assert response["X-Custom"] == "async-hello"
        assert "token" in response.cookies


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
