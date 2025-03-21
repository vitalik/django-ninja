from typing import TYPE_CHECKING, Any, NoReturn

from django.http import Http404, HttpRequest, HttpResponse

from ninja.openapi.docs import DocsBase
from ninja.responses import Response

if TYPE_CHECKING:
    # if anyone knows a cleaner way to make mypy happy - welcome
    from ninja import NinjaAPI  # pragma: no cover


def default_home(request: HttpRequest, api: "NinjaAPI", **kwargs: Any) -> NoReturn:
    "This view is mainly needed to determine the full path for API operations"
    docs_url = f"{request.path}{api.docs_url}".replace("//", "/")
    raise Http404(f"docs_url = {docs_url}")


def openapi_json(request: HttpRequest, api: "NinjaAPI", **kwargs: Any) -> HttpResponse:
    schema = api.get_openapi_schema(path_params=kwargs)
    return Response(schema)


def openapi_view(request: HttpRequest, api: "NinjaAPI", **kwargs: Any) -> HttpResponse:
    docs: DocsBase = api.docs
    return docs.render_page(request, api, **kwargs)
