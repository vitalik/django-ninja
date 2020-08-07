from ninja.responses import Response
from django.http import Http404
from django.urls import reverse
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # if anyone konw a cleaner way to make mypy happy - welcome
    from ninja import NinjaAPI  # pragma: no cover


def default_home(request, api: "NinjaAPI"):
    "This view is mainly needed to determine the full path for API operations"
    docs_url = f"{request.path}{api.docs_url}".replace("//", "/")
    raise Http404(f"docs_url = {docs_url}")


def openapi_json(request, api: "NinjaAPI"):
    schema = api.get_openapi_schema()
    return Response(schema)


def swagger(request, api: "NinjaAPI"):
    return render(
        request,
        "ninja/swagger.html",
        {"api": api, "openapi_json_url": reverse(f"{api.urls_namespace}:openapi-json")},
    )


def render(request, template_name, context=None):
    """
    I do not relly want ninja to be required in INSTALLED_APPS for now
    that is why for now we use this render function to simulate django render
    """
    import os
    from django.template import Template, RequestContext
    from django.http import HttpResponse

    tpl_file = os.path.join(os.path.dirname(__file__), "../templates", template_name)
    with open(tpl_file) as f:
        tpl = Template(f.read())
    html = tpl.render(RequestContext(request, context))
    return HttpResponse(html)
