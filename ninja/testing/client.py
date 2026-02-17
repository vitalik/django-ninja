from json import dumps as json_dumps
from json import loads as json_loads
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
from unittest.mock import Mock

from django.http import QueryDict, StreamingHttpResponse
from django.http.request import HttpRequest

from ninja import NinjaAPI, Router
from ninja.responses import NinjaJSONEncoder
from ninja.responses import Response as HttpResponse


# TODO: this should be changed
# maybe add here urlconf object and add urls from here
class NinjaClientBase:
    __test__ = False  # <- skip pytest

    def __init__(
        self,
        router_or_app: Union[NinjaAPI, Router],
        headers: Optional[Dict[str, str]] = None,
        COOKIES: Optional[Dict[str, str]] = None,
    ) -> None:
        self.headers = headers or {}
        self.cookies = COOKIES or {}
        self.router_or_app = router_or_app

    def get(
        self, path: str, data: Optional[Dict] = None, **request_params: Any
    ) -> "NinjaResponse":
        return self.request("GET", path, data, **request_params)

    def post(
        self,
        path: str,
        data: Optional[Dict] = None,
        json: Any = None,
        **request_params: Any,
    ) -> "NinjaResponse":
        return self.request("POST", path, data, json, **request_params)

    def patch(
        self,
        path: str,
        data: Optional[Dict] = None,
        json: Any = None,
        **request_params: Any,
    ) -> "NinjaResponse":
        return self.request("PATCH", path, data, json, **request_params)

    def put(
        self,
        path: str,
        data: Optional[Dict] = None,
        json: Any = None,
        **request_params: Any,
    ) -> "NinjaResponse":
        return self.request("PUT", path, data, json, **request_params)

    def delete(
        self,
        path: str,
        data: Optional[Dict] = None,
        json: Any = None,
        **request_params: Any,
    ) -> "NinjaResponse":
        return self.request("DELETE", path, data, json, **request_params)

    def request(
        self,
        method: str,
        path: str,
        data: Optional[Dict] = None,
        json: Any = None,
        **request_params: Any,
    ) -> "NinjaResponse":
        if json is not None:
            request_params["body"] = json_dumps(json, cls=NinjaJSONEncoder)
        if data is None:
            data = {}
        if self.headers or request_params.get("headers"):
            request_params["headers"] = {
                **self.headers,
                **request_params.get("headers", {}),
            }
        if self.cookies or request_params.get("COOKIES"):
            request_params["COOKIES"] = {
                **self.cookies,
                **request_params.get("COOKIES", {}),
            }
        func, request, kwargs = self._resolve(method, path, data, request_params)
        return self._call(func, request, kwargs)  # type: ignore

    @property
    def urls(self) -> List:
        if not hasattr(self, "_urls_cache"):
            self._urls_cache: List
            if isinstance(self.router_or_app, NinjaAPI):
                self._urls_cache = self.router_or_app.urls[0]
            else:
                # Create temporary API without mutating router
                # Unique namespace prevents registry conflicts
                api = NinjaAPI(urls_namespace=f"test-{id(self)}")
                api.add_router("", self.router_or_app)
                self._urls_cache = api.urls[0]
        return self._urls_cache

    def _resolve(
        self, method: str, path: str, data: Dict, request_params: Dict[str, Any]
    ) -> Tuple[Callable, HttpRequest, Dict]:
        url_path = path.split("?")[0].lstrip("/")
        for url in self.urls:
            match = url.resolve(url_path)
            if match:
                request = self._build_request(method, path, data, request_params)
                return match.func, request, match.kwargs
        raise Exception(f'Cannot resolve "{path}"')

    def _build_request(
        self, method: str, path: str, data: Dict, request_params: Dict[str, Any]
    ) -> HttpRequest:
        request = HttpRequest()
        request.method = method
        body = request_params.pop("body", b"")
        request._body = body.encode() if isinstance(body, str) else body
        request._dont_enforce_csrf_checks = True

        request.auth = None
        if "user" not in request_params:
            request.user = Mock()
            request.user.is_authenticated = False
            request.user.is_staff = False
            request.user.is_superuser = False

        files = request_params.pop("FILES", None)
        if files is not None:
            request.FILES = files

        if isinstance(data, QueryDict):
            request.POST = data
        elif isinstance(data, (str, bytes)):
            request._body = data.encode() if isinstance(data, str) else data
        elif data:
            for k, v in data.items():
                request.POST[k] = v

        query_params = request_params.pop("query_params", None)
        if "?" in path:
            path, query_string = path.split("?", maxsplit=1)
            request.GET = QueryDict(query_string)
        elif query_params is not None:
            for k, v in query_params.items():
                if isinstance(v, list):
                    for item in v:
                        request.GET.appendlist(k, item)
                else:
                    request.GET[k] = v
        request.path = path
        # If "settings.FORCE_SCRIPT_NAME" is set, "request.path_info" ought
        # to respect it, but this class skips the Django URL resolver,
        # so don't bother
        request.path_info = path

        request.META = request_params.pop(
            "META",
            {
                "REQUEST_METHOD": request.method,
                "SCRIPT_NAME": "",
                "PATH_INFO": request.path_info,
                "QUERY_STRING": request.GET.urlencode(),
                "SERVER_NAME": "testserver",
                "SERVER_PORT": "80",
                "SERVER_PROTOCOL": "HTTP/1.1",
                "REMOTE_ADDR": "127.0.0.1",
            },
        )
        request.META.update({
            f"HTTP_{k.replace('-', '_')}": v
            for k, v in request_params.pop("headers", {}).items()
        })

        for k, v in request_params.items():
            setattr(request, k, v)
        return request


class TestClient(NinjaClientBase):
    def _call(
        self, func: Callable, request: HttpRequest, kwargs: Dict
    ) -> "NinjaResponse":
        return NinjaResponse(func(request, **kwargs))


class TestAsyncClient(NinjaClientBase):
    async def _call(
        self, func: Callable, request: HttpRequest, kwargs: Dict
    ) -> "NinjaResponse":
        return NinjaResponse(await func(request, **kwargs))


class NinjaResponse:
    def __init__(self, http_response: Union[HttpResponse, StreamingHttpResponse]):
        self._response = http_response
        self.status_code = http_response.status_code
        self.streaming = http_response.streaming
        if self.streaming:
            self.content = b"".join(http_response.streaming_content)  # type: ignore
        else:
            self.content = http_response.content
        self._data = None

    def json(self) -> Any:
        return json_loads(self.content)

    @property
    def data(self) -> Any:
        if self._data is None:  # Recomputes if json() is None but cheap then
            self._data = self.json()
        return self._data

    def __getitem__(self, key: str) -> Any:
        return self._response[key]

    def __getattr__(self, attr: str) -> Any:
        return getattr(self._response, attr)
