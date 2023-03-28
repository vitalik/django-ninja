from unittest import mock

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory, TestCase, override_settings

from ninja import File, NinjaAPI, UploadedFile
from ninja.middlewares import process_put_patch
from ninja.testing import TestAsyncClient, TestClient


@override_settings(MIDDLEWARES=("ninja.middlewares.process_put_patch"))
def test_sync_patch_put_middleware():
    api = NinjaAPI()

    @api.patch("/sync/random-file")
    def sync_patch_random_file(request, file: UploadedFile = File(...)):
        return {"name": file.name, "data": file.read().decode()}

    @api.put("/sync/random-file")
    def sync_put_random_file(request, file: UploadedFile = File(...)):
        return {"name": file.name, "data": file.read().decode()}

    # Test Client
    client = TestClient(api)

    response = client.patch("/sync/random-file")  # no file
    assert response.status_code == 422

    response = client.put("/sync/random-file")  # no file
    assert response.status_code == 422

    file = SimpleUploadedFile("django.txt", b"django-rocks")
    response = client.patch("/sync/random-file", FILES={"file": file})
    assert response.status_code == 200
    assert response.json() == {"name": "django.txt", "data": "django-rocks"}

    file = SimpleUploadedFile("foo.txt", b"bar")
    response = client.put("/sync/random-file", FILES={"file": file})
    assert response.status_code == 200
    assert response.json() == {"name": "foo.txt", "data": "bar"}


@pytest.mark.asyncio
@override_settings(MIDDLEWARES=("ninja.middlewares.process_put_patch"))
async def test_async_patch_put_middleware():
    api = NinjaAPI()

    @api.patch("/async/random-file")
    async def async_patch_random_file(request, file: UploadedFile = File(...)):
        return {"name": file.name, "data": file.read().decode()}

    @api.put("/async/random-file")
    async def async_put_random_file(request, file: UploadedFile = File(...)):
        return {"name": file.name, "data": file.read().decode()}

    client = TestAsyncClient(api)

    response = await client.patch("/async/random-file")  # no file
    assert response.status_code == 422

    response = await client.put("/async/random-file")  # no file
    assert response.status_code == 422

    file = SimpleUploadedFile("django.txt", b"django-rocks")
    response = await client.patch("/async/random-file", FILES={"file": file})
    assert response.status_code == 200
    assert response.json() == {"name": "django.txt", "data": "django-rocks"}

    file = SimpleUploadedFile("foo.txt", b"bar")
    response = await client.put("/async/random-file", FILES={"file": file})
    assert response.status_code == 200
    assert response.json() == {"name": "foo.txt", "data": "bar"}


@override_settings(ROOT_URLCONF="middleware.urls")
class TestMiddleware(TestCase):
    def setUp(self) -> None:
        self.factory = RequestFactory()

    def test_middleware(self):
        get_response = mock.MagicMock()
        request = self.factory.get("/")

        middleware = process_put_patch(get_response)
        response = middleware(request)

        # ensure get_response has been returned
        # (or not, if your middleware does something else)
        self.assertEqual(get_response.return_value, response)
