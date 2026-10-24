import json
import warnings

import pytest
from django.http import HttpResponse, StreamingHttpResponse

from ninja.compatibility.streaming import _AsyncOnly, create_streaming_response

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


@async_api.get("/jsonl/with-headers", response=JSONL[Item])
async def async_jsonl_with_headers(request, response: HttpResponse):
    response["X-Custom"] = "async-hello"
    response.set_cookie("token", "xyz")
    yield {"name": "async-headers", "price": 0.0}


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


# --- Async detection regression tests (issue #1714) ---
#
# Django's StreamingHttpResponse detects async content by trying
# iter(value) first and falling back to aiter(value) on TypeError.
# Async iterators for which iter() does not raise are misclassified
# as synchronous (is_async=False), which makes Django's ASGI handler
# warn on every request and consume the stream via sync_to_async(list).
# create_streaming_response must therefore hand Django an object that
# only exposes __aiter__.


class _TrapAsyncIterator:
    """An async iterator that also defines __iter__ (the detection trap).

    Passed to StreamingHttpResponse directly, Django classifies this as
    synchronous because iter() succeeds.  It must still be served as an
    async stream when it goes through the compatibility wrapper.
    """

    def __init__(self, chunks):
        self._chunks = list(chunks)

    def __aiter__(self):
        return self

    async def __anext__(self):
        if not self._chunks:
            raise StopAsyncIteration
        return self._chunks.pop(0)

    def __iter__(self):
        return iter([])


class TestAsyncOnlyWrapper:
    def test_wrapper_has_no_sync_iterator(self):
        async def gen():
            yield b"x"

        wrapper = _AsyncOnly(gen())
        with pytest.raises(TypeError):
            iter(wrapper)

    @pytest.mark.asyncio
    async def test_wrapper_delegates_async_iteration(self):
        async def gen():
            yield b"a"
            yield b"b"

        wrapper = _AsyncOnly(gen())
        assert [chunk async for chunk in wrapper] == [b"a", b"b"]

    @pytest.mark.asyncio
    async def test_wrapper_makes_trap_iterator_detected_as_async(self):
        response = StreamingHttpResponse(
            _AsyncOnly(_TrapAsyncIterator([b"one", b"two"])),
            content_type="text/event-stream",
            status=200,
        )
        assert response.is_async is True
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            chunks = [chunk async for chunk in response]
        assert chunks == [b"one", b"two"]

    @pytest.mark.asyncio
    async def test_wrapper_aclose_forwards_to_generator(self):
        closed = False

        async def gen():
            nonlocal closed
            try:
                yield b"x"
                yield b"y"
            finally:
                closed = True

        wrapper = _AsyncOnly(gen())
        assert await anext(wrapper.__aiter__()) == b"x"
        await wrapper.aclose()
        assert closed is True


@pytest.mark.asyncio
class TestCreateStreamingResponseAsyncDetection:
    async def test_response_is_detected_as_async(self):
        async def gen():
            yield b"data: 1\n\n"
            yield b"data: 2\n\n"

        temporal_response = HttpResponse()
        temporal_response["X-Custom"] = "lazy"

        response = await create_streaming_response(
            gen(),
            content_type="text/event-stream",
            status=200,
            temporal_response=temporal_response,
            extra_headers={"Cache-Control": "no-cache"},
        )

        assert response.is_async is True
        assert response["Cache-Control"] == "no-cache"

        with warnings.catch_warnings():
            # The "synchronous iterators" warning must not fire.
            warnings.simplefilter("error")
            chunks = [chunk async for chunk in response]
        assert b"".join(chunks) == b"data: 1\n\ndata: 2\n\n"
        # Lazy temporal headers are copied once the stream is exhausted.
        assert response["X-Custom"] == "lazy"

    async def test_async_client_sse_emits_no_sync_iterator_warning(self):
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "error", message=".*synchronous iterators.*|.*asynchronous iterators.*"
            )
            response = await async_client.get("/sse/items")
        assert response.status_code == 200
        content = response.content.decode()
        assert len(content.strip().split("\n\n")) == 3
