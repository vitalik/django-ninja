from typing import TYPE_CHECKING, NoReturn, Optional

from django.conf import settings
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import render
from django.urls import reverse

from ninja.conf import settings as ninja_settings
from ninja.responses import Response
from ninja.types import DictStrAny

if TYPE_CHECKING:
    # if anyone knows a cleaner way to make mypy happy - welcome
    from ninja import NinjaAPI  # pragma: no cover

__all__ = ["default_home", "openapi_json", "openapi_view", "openapi_view_cdn"]


render_swagger = ninja_settings.DOCS_VIEW == "swagger"
view_tpl = "ninja/swagger.html" if render_swagger else "ninja/redoc.html"
view_cdn_tpl = (
    "../templates/ninja/swagger_cdn.html"
    if render_swagger
    else "../templates/ninja/redoc_cdn.html"
)


def default_home(request: HttpRequest, api: "NinjaAPI") -> NoReturn:
    "This view is mainly needed to determine the full path for API operations"
    docs_url = f"{request.path}{api.docs_url}".replace("//", "/")
    raise Http404(f"docs_url = {docs_url}")


def openapi_json(request: HttpRequest, api: "NinjaAPI") -> HttpResponse:
    schema = api.get_openapi_schema()
    return Response(schema)


def openapi_view(request: HttpRequest, api: "NinjaAPI") -> HttpResponse:
    """
    I do not really want ninja to be required in INSTALLED_APPS for now
    so we automatically detect - if ninja is in INSTALLED_APPS - then we render with django.shortcuts.render
    otherwise - rendering custom html with swagger js from cdn
    """
    context = {
        "api": api,
        "openapi_json_url": reverse(f"{api.urls_namespace}:openapi-json"),
    }
    if "ninja" in settings.INSTALLED_APPS:
        return render(request, view_tpl, context)
    else:
        return openapi_view_cdn(request, context)


def openapi_view_cdn(
    request: HttpRequest, context: Optional[DictStrAny] = None
) -> HttpResponse:
    import os

    from django.http import HttpResponse
    from django.template import RequestContext, Template

    tpl_file = os.path.join(os.path.dirname(__file__), view_cdn_tpl)
    with open(tpl_file) as f:
        tpl = Template(f.read())
    html = tpl.render(RequestContext(request, context))
    return HttpResponse(html)
