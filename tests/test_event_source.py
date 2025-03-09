import asyncio

import pytest

from ninja import NinjaAPI
from ninja.testing import TestClient

messages = [
    "lorem",
    "ipsum",
    "dolor",
    "sit",
    "amet",
    "consectetur",
    "adipiscing",
    "elit",
]


@pytest.mark.asyncio
async def test_async_event_source():
    api = NinjaAPI()

    @api.event_source("/event_source_delay")
    async def async_event_source_op(request):
        for message in messages:
            await asyncio.sleep(0.0)
            yield f"data: {message}\n\n"

    client = TestClient(api)

    response = client.get("/event_source_delay")

    assert response.status_code == 200

    expected_content = b"".join(
        [f"data: {message}\n\n".encode() for message in messages]
    )
    assert expected_content == await response.content


def test_sync_event_source():
    api = NinjaAPI()

    @api.event_source("/event_source")
    def sync_event_source_op(request):
        for message in messages:
            yield f"data: {message}\n\n"

    client = TestClient(api)

    response = client.get("/event_source")

    assert response.status_code == 200

    expected_content = b"".join(
        [f"data: {message}\n\n".encode() for message in messages]
    )
    assert response.content == expected_content
