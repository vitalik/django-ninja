from ninja import NinjaAPI
from ninja.testing import TestClient

api = NinjaAPI()

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


@api.event_source("/event_source")
def event_source_op(request):
    for message in messages:
        yield f"data: {message}\n\n"


client = TestClient(api)


def test_event_source_op():
    response = client.get("/event_source")

    assert response.status_code == 200

    expected_content = b"".join(
        [f"data: {message}\n\n".encode() for message in messages]
    )
    assert response.content == expected_content
