from unittest.mock import Mock

from django.test import override_settings

from ninja import NinjaAPI
from ninja.openapi.urls import get_openapi_urls

# TODO: Test passing the doc_context for Redoc
# TODO: Test passing the doc_context to cdn templates


def test_openapi_docs_context_swagger():
    "Test providing docs_context to Swagger"
    api = NinjaAPI(docs_context={"swagger": {"filter": True}})

    paths = get_openapi_urls(api)
    assert len(paths) == 2
    doc_path = paths[1]

    response = doc_path.callback(Mock())
    assert response.status_code == 200
    assert b'{"filter": true}' in response.content


def test_openapi_docs_context_swagger_misconfigured():
    "Test providing docs_context to Redoc when Swagger is configured"
    api = NinjaAPI(docs_context={"redoc": {"filter": True}})

    paths = get_openapi_urls(api)
    assert len(paths) == 2
    doc_path = paths[1]

    response = doc_path.callback(Mock())
    assert response.status_code == 200
    assert b'{"filter": true}' not in response.content
