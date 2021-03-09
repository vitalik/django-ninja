from functools import partial
from typing import TYPE_CHECKING

from django.urls import path

from .views import default_home, openapi_json, swagger

if TYPE_CHECKING:
    from ninja import NinjaAPI


def get_openapi_urls(api: "NinjaAPI"):
    result = []

    if api.openapi_url:
        result.append(
            path(
                api.openapi_url.lstrip("/"),
                partial(openapi_json, api=api),
                name="openapi-json",
            )
        )

        assert (
            api.openapi_url != api.docs_url
        ), "Please use different urls for openapi_url and docs_url"

        if api.docs_url:
            result.append(
                path(
                    api.docs_url.lstrip("/"),
                    partial(swagger, api=api),
                    name="openapi-swagger",
                )
            )

    return result


def get_root_url(api: "NinjaAPI"):
    return path("", partial(default_home, api=api), name="api-root")
