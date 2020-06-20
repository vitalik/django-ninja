from ninja.security.base import AuthBase
from ninja.compatibility.request import get_headers


class APIKeyBase(AuthBase):
    openapi_type = "apiKey"
    param_name = "key"

    def __init__(self):
        self.openapi_name = self.param_name
        super().__init__()

    def __call__(self, request):
        key = self._get_key(request)
        return self.authenticate(request, key)

    def authenticate(self, request, key):
        raise NotImplementedError("Please implement authenticate(self, request, key)")


class APIKeyQuery(APIKeyBase):
    openapi_in = "query"

    def _get_key(self, request):
        return request.GET.get(self.param_name)


class APIKeyCookie(APIKeyBase):
    openapi_in = "cookie"

    def _get_key(self, request):
        return request.COOKIES.get(self.param_name)


class APIKeyHeader(APIKeyBase):
    openapi_in = "header"

    def _get_key(self, request):
        headers = get_headers(request)
        return headers.get(self.param_name)
