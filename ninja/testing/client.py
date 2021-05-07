from json import dumps as json_dumps, loads as json_loads
from typing import Any, Callable, Dict, List, Tuple, Union
from unittest.mock import Mock

import django
from django.http import QueryDict
from django.urls.resolvers import URLPattern

from ninja import NinjaAPI, Router
from ninja.responses import Response as HttpResponse


# TODO: this should be changed
# maybe add here urlconf object and add urls from here
class NinjaClientBase:
    __test__ = False  # <- skip pytest

    def __init__(self, router_or_app: Union[NinjaAPI, Router]) -> None:
        self.router_or_app = router_or_app

    def get(
        self, path: str, data: Dict = {}, **request_params: Dict
    ) -> "NinjaResponse":
        return self.request("GET", path, data, **request_params)

    def post(
        self, path: str, data: Dict = {}, json: Any = None, **request_params: Any
    ) -> "NinjaResponse":
        return self.request("POST", path, data, json, **request_params)

    def patch(
        self, path: str, data: Dict = {}, json: Any = None, **request_params: Any
    ) -> "NinjaResponse":
        return self.request("PATCH", path, data, json, **request_params)

    def put(
        self, path: str, data: Dict = {}, json: Any = None, **request_params: Any
    ) -> "NinjaResponse":
        return self.request("PUT", path, data, json, **request_params)

    def delete(
        self, path: str, data: Dict = {}, json: Any = None, **request_params: Any
    ) -> "NinjaResponse":
        return self.request("DELETE", path, data, json, **request_params)

    def request(
        self,
        method: str,
        path: str,
        data: Dict = {},
        json: Any = None,
        **request_params: Any,
    ) -> "NinjaResponse":
        if json is not None:
            request_params["body"] = json_dumps(json)
        func, request, kwargs = self._resolve(method, path, data, request_params)
        return self._call(func, request, kwargs)  # type: ignore

    @property
    def urls(self) -> List[URLPattern]:
        if not hasattr(self, "_urls_cache"):
            self._urls_cache: List[URLPattern]
            if isinstance(self.router_or_app, NinjaAPI):
                self._urls_cache = self.router_or_app.urls[0]
            else:
                api = NinjaAPI()
                self.router_or_app.set_api_instance(api)
                self._urls_cache = list(self.router_or_app.urls_paths(""))
        return self._urls_cache

    def _resolve(
        self, method: str, path: str, data: Dict, request_params: Any
    ) -> Tuple[Callable, Mock, Dict]:
        url_path = path.split("?")[0].lstrip("/")
        for url in self.urls:
            match = url.resolve(url_path)
            if match:
                request = self._build_request(method, path, data, request_params)
                return match.func, request, match.kwargs
        raise Exception(f'Cannot resolve "{path}"')

    def _build_request(
        self, method: str, path: str, data: Dict, request_params: Any
    ) -> Mock:
        request = Mock()
        request.method = method
        request.path = path
        request.body = ""
        request.COOKIES = {}
        request._dont_enforce_csrf_checks = False
        request.is_secure.return_value = False

        if "user" not in request_params:
            request.user.is_authenticated = False

        request.META = request_params.pop("META", {})
        request.FILES = request_params.pop("FILES", {})

        request.META.update(
            dict(
                [
                    (f"HTTP_{k.replace('-', '_')}", v)
                    for k, v in request_params.pop("headers", {}).items()
                ]
            )
        )
        if django.VERSION[:2] > (2, 1):
            from django.http.request import HttpHeaders

            request.headers = HttpHeaders(request.META)

        if isinstance(data, QueryDict):
            request.POST = data
        else:
            request.POST = QueryDict(mutable=True)
            for k, v in data.items():
                request.POST[k] = v

        if "?" in path:
            request.GET = QueryDict(path.split("?")[1])
        else:
            request.GET = QueryDict()

        for k, v in request_params.items():
            setattr(request, k, v)
        return request


class TestClient(NinjaClientBase):
    def _call(self, func: Callable, request: Mock, kwargs: Dict) -> "NinjaResponse":
        return NinjaResponse(func(request, **kwargs))


class TestAsyncClient(NinjaClientBase):
    async def _call(
        self, func: Callable, request: Mock, kwargs: Dict
    ) -> "NinjaResponse":
        return NinjaResponse(await func(request, **kwargs))


class NinjaResponse:
    def __init__(self, http_response: HttpResponse):
        # TODO: what's the type here ?
        self._response = http_response
        self.status_code = http_response.status_code
        self.content = http_response.content

    def json(self) -> Any:
        return json_loads(self.content)

    def __getitem__(self, key: str) -> Any:
        return self._response[key]
