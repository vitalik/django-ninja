from functools import partial
from django.urls import path
from .views import openapi_json, swagger, home


def get_openapi_urls(api: "NinjaAPI"):
    result = [path("", partial(home, api=api), name=f"api-root")]

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
