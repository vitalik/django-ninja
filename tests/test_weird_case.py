
from ninja import NinjaAPI
from ninja.security import (
    HttpBearer,
)
from ninja.testing import TestAsyncClient, TestClient


class SyncBearerAuth(HttpBearer):
    def authenticate(self, request, token: str):
        return


class AsyncBearerAuth(HttpBearer):
    async def authenticate(self, request, token: str):
        return


api = NinjaAPI()


@api.get("/sync/", auth=SyncBearerAuth())
def sync_auth(request):
    return


@api.get("/async/", auth=AsyncBearerAuth())
def async_auth(request):
    return


client = TestClient(api)
async_client = TestAsyncClient(api)


def test_async_bearer_invalid_bearer():
    # TypeError: object NoneType can't be used in 'await' expression
    response = client.get("/async/", headers={"Authorization": "Bearer 123"})
    assert response.status_code == 401


def test_async_bearer_no_bearer():
    response = client.get("/async/")
    assert response.status_code == 401


def test_sync_bearer_no_berer():
    response = client.get("/sync/")
    assert response.status_code == 401
