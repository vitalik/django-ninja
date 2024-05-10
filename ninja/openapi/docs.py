import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Iterator, Optional, Union

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.urls import reverse

from ninja.router import Router
from ninja.types import DictStrAny

if TYPE_CHECKING:
    # if anyone knows a cleaner way to make mypy happy - welcome
    from ninja import NinjaAPI  # pragma: no cover

ABS_TPL_PATH = Path(__file__).parent.parent / "templates/ninja/"


class DocsBase(ABC):
    @abstractmethod
    def render_page(
        self, request: HttpRequest, api: "NinjaAPI", **kwargs: Any
    ) -> HttpResponse:
        pass  # pragma: no cover

    def get_openapi_url(self, api: "NinjaAPI", path_params: DictStrAny) -> str:
        return reverse(f"{api.urls_namespace}:openapi-json", kwargs=path_params)


class Swagger(DocsBase):
    template = "ninja/swagger.html"
    template_cdn = str(ABS_TPL_PATH / "swagger_cdn.html")
    default_settings = {
        "layout": "BaseLayout",
        "deepLinking": True,
    }

    def __init__(self, settings: Optional[DictStrAny] = None):
        self.settings = {}
        self.settings.update(self.default_settings)
        if settings:
            self.settings.update(settings)

    def render_page(
        self, request: HttpRequest, api: "NinjaAPI", **kwargs: Any
    ) -> HttpResponse:
        self.settings["url"] = self.get_openapi_url(api, kwargs)
        context = {
            "swagger_settings": json.dumps(self.settings, indent=1),
            "api": api,
            "add_csrf": _csrf_needed(api),
        }
        return render_template(request, self.template, self.template_cdn, context)


class Redoc(DocsBase):
    template = "ninja/redoc.html"
    template_cdn = str(ABS_TPL_PATH / "redoc_cdn.html")
    default_settings: DictStrAny = {}

    def __init__(self, settings: Optional[DictStrAny] = None):
        self.settings = {}
        self.settings.update(self.default_settings)
        if settings:
            self.settings.update(settings)

    def render_page(
        self, request: HttpRequest, api: "NinjaAPI", **kwargs: Any
    ) -> HttpResponse:
        context = {
            "redoc_settings": json.dumps(self.settings, indent=1),
            "openapi_json_url": self.get_openapi_url(api, kwargs),
            "api": api,
        }
        return render_template(request, self.template, self.template_cdn, context)


def render_template(
    request: HttpRequest, template: str, template_cdn: str, context: DictStrAny
) -> HttpResponse:
    """
    I do not really want ninja to be required in INSTALLED_APPS to ease installation
    so it automatically detects - if ninja is in INSTALLED_APPS - then we render with django.shortcuts.render
    otherwise - rendering custom html with swagger js from cdn
    """
    if "ninja" in settings.INSTALLED_APPS:
        return render(request, template, context)
    else:
        return _render_cdn_template(request, template_cdn, context)


def _render_cdn_template(
    request: HttpRequest, template_path: str, context: Optional[DictStrAny] = None
) -> HttpResponse:
    "this is helper to find and render html template when ninja is not in INSTALLED_APPS"
    from django.template import RequestContext, Template

    tpl = Template(Path(template_path).read_text())
    html = tpl.render(RequestContext(request, context))
    return HttpResponse(html)


def _iter_auth_callbacks(
    api_or_router: Union["NinjaAPI", Router],
) -> Iterator[Callable[..., Any]]:
    """this is helper to iterate over all operations in api or router"""
    if isinstance(api_or_router, Router):
        for _, path_view in api_or_router.path_operations.items():
            for operation in path_view.operations:
                yield from operation.auth_callbacks
    for _, router in api_or_router._routers:  # noqa
        yield from _iter_auth_callbacks(router)


def _csrf_needed(api: "NinjaAPI") -> bool:
    add_csrf: Optional[bool] = getattr(api, "_add_csrf", None)
    if add_csrf is not None:
        return add_csrf
    for auth_callback in _iter_auth_callbacks(api):
        if getattr(auth_callback, "csrf", False):
            api._add_csrf = True  # type: ignore[attr-defined]
            return True
    api._add_csrf = False  # type: ignore[attr-defined]
    return False
