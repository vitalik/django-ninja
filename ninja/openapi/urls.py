from typing import TYPE_CHECKING, Any, List

from django.urls import path

from .views import default_home, openapi_json, openapi_view

if TYPE_CHECKING:
    from ninja import NinjaAPI  # pragma: no cover

__all__ = ["get_openapi_urls", "get_root_url"]


def get_openapi_urls(api: "NinjaAPI") -> List[Any]:
    result = []

    if api.openapi_url:
        view = openapi_json
        if api.docs_decorator:
            view = api.docs_decorator(view)  # type: ignore
        result.append(
            path(api.openapi_url.lstrip("/"), view, {"api": api}, name="openapi-json"),
        )

        assert (
            api.openapi_url != api.docs_url
        ), "Please use different urls for openapi_url and docs_url"

        if api.docs_url:
            view = openapi_view
            if api.docs_decorator:
                view = api.docs_decorator(view)  # type: ignore
            result.append(
                path(api.docs_url.lstrip("/"), view, {"api": api}, name="openapi-view"),
            )

    return result


def get_root_url(api: "NinjaAPI") -> Any:
    return path("", default_home, {"api": api}, name="api-root")
