from json import loads as json_loads, dumps as json_dumps
from ninja import NinjaAPI
from unittest.mock import Mock
import django
from django.http import QueryDict


# TODO: this should be changed
# maybe add here urlconf object and add urls from here
class NinjaClientBase:
    def __init__(self, router_or_app):
        if isinstance(router_or_app, NinjaAPI):
            self.router = router_or_app.default_router
        else:
            self.router = router_or_app
        self.urls = list(self.router.urls_paths(""))

    def get(self, path, data={}, **request_params):
        return self.request("GET", path, data, **request_params)

    def post(self, path, data={}, json=None, **request_params):
        return self.request("POST", path, data, json, **request_params)

    def patch(self, path, data={}, json=None, **request_params):
        return self.request("PATCH", path, data, json, **request_params)

    def put(self, path, data={}, json=None, **request_params):
        return self.request("PUT", path, data, json, **request_params)

    def delete(self, path, data={}, json=None, **request_params):
        return self.request("DELETE", path, data, json, **request_params)

    def request(self, method, path, data={}, json=None, **request_params):
        if json is not None:
            request_params["body"] = json_dumps(json)
        func, request, kwargs = self._resolve(method, path, data, request_params)
        return self._call(func, request, kwargs)

    def _resolve(self, method, path, data, request_params):
        url_path = path.split("?")[0].lstrip("/")
        for url in self.urls:
            match = url.resolve(url_path)
            if match:
                request = self._build_request(method, path, data, request_params)
                return match.func, request, match.kwargs
        raise Exception(f'Cannot resolve "{path}"')

    def _build_request(self, method: str, path: str, data: dict, request_params: dict):
        request = Mock()
        request.method = method
        request.path = path
        request.body = ""
        request.COOKIES = {}

        if "user" not in request_params:
            request.user.is_authenticated = False

        request.META = request_params.pop("META", {})

        request.META.update(
            dict(
                [(f"HTTP_{k}", v) for k, v in request_params.pop("headers", {}).items()]
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


class NinjaClient(NinjaClientBase):
    def _call(self, func, request, kwargs):
        return NinjaResponse(func(request, **kwargs))


class NinjaAsyncClient(NinjaClientBase):
    async def _call(self, func, request, kwargs):
        return NinjaResponse(await func(request, **kwargs))


class NinjaResponse:
    def __init__(self, http_response):
        self._response = http_response
        self.status_code = http_response.status_code
        self.content = http_response.content

    def json(self):
        return json_loads(self.content)
