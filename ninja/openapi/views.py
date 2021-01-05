from ninja.responses import Response
from django.http import Http404
from django.conf import settings
from django.shortcuts import render
from django.urls import reverse
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # if anyone knows a cleaner way to make mypy happy - welcome
    from ninja import NinjaAPI  # pragma: no cover


def default_home(request, api: "NinjaAPI"):
    "This view is mainly needed to determine the full path for API operations"
    docs_url = f"{request.path}{api.docs_url}".replace("//", "/")
    raise Http404(f"docs_url = {docs_url}")


def openapi_json(request, api: "NinjaAPI"):
    schema = api.get_openapi_schema()
    return Response(schema)


def swagger(request, api: "NinjaAPI"):
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
        return render(request, "ninja/swagger.html", context)
    else:
        return swagger_cdn(request, context)


def swagger_cdn(request, context=None):
    import os
    from django.template import Template, RequestContext
    from django.http import HttpResponse

    tpl_file = os.path.join(
        os.path.dirname(__file__), "../templates/ninja/swagger_cdn.html"
    )
    with open(tpl_file) as f:
        tpl = Template(f.read())
    html = tpl.render(RequestContext(request, context))
    return HttpResponse(html)
