import os
from ninja.openapi import get_schema
from typing import List, Optional, Tuple, Sequence, Union, Callable
from django.urls import reverse
from ninja.openapi.urls import get_openapi_urls, get_root_url
from ninja.router import Router
from ninja.errors import ConfigError
from ninja.constants import NOT_SET


class NinjaAPI:
    _registry: List[str] = []

    def __init__(
        self,
        *,
        title: str = "NinjaAPI",
        version: str = "1.0.0",
        description: str = "",
        openapi_url: Optional[str] = "/openapi.json",
        docs_url: Optional[str] = "/docs",
        urls_namespace: str = None,
        auth: Union[Sequence[Callable], Callable, object] = NOT_SET,
    ):
        self.title = title
        self.version = version
        self.description = description
        self.openapi_url = openapi_url
        self.docs_url = docs_url
        self.urls_namespace = urls_namespace or f"api-{self.version}"
        self.auth: Optional[Sequence[Callable]] = NOT_SET
        if auth is not None and auth is not NOT_SET:
            self.auth = isinstance(auth, Sequence) and auth or [auth]

        self._validate()

        self._routers: List[Tuple[str, Router]] = []
        self.default_router = Router()
        self.add_router("", self.default_router)

    def get(self, path: str, *, auth=NOT_SET, response=None):
        return self.default_router.get(
            path, auth=auth is NOT_SET and self.auth or auth, response=response
        )

    def post(self, path: str, *, auth=NOT_SET, response=None):
        return self.default_router.post(
            path, auth=auth is NOT_SET and self.auth or auth, response=response
        )

    def delete(self, path: str, *, auth=NOT_SET, response=None):
        return self.default_router.delete(
            path, auth=auth is NOT_SET and self.auth or auth, response=response
        )

    def patch(self, path: str, *, auth=NOT_SET, response=None):
        return self.default_router.patch(
            path, auth=auth is NOT_SET and self.auth or auth, response=response
        )

    def put(self, path: str, *, auth=NOT_SET, response=None):
        return self.default_router.put(
            path, auth=auth is NOT_SET and self.auth or auth, response=response
        )

    def api_operation(
        self, methods: List[str], path: str, *, auth=NOT_SET, response=None
    ):
        return self.default_router.api_operation(
            methods, path, auth=auth is NOT_SET and self.auth or auth, response=response
        )

    def add_router(self, prefix, router):
        self._routers.append((prefix, router))

    @property
    def urls(self):
        return (
            self._get_urls(),
            "ninja",
            self.urls_namespace,
        )

    def _get_urls(self):
        result = get_openapi_urls(self)

        for prefix, router in self._routers:
            for path in router.urls_paths(prefix):
                result.append(path)

        result.append(get_root_url(self))
        return result

    @property
    def root_path(self):
        name = f"{self.urls_namespace}:api-root"
        return reverse(name)

    def get_openapi_schema(self, path_prefix=None):
        if path_prefix is None:
            path_prefix = self.root_path
        return get_schema(api=self, path_prefix=path_prefix)

    def _validate(self):
        skip_registry = os.environ.get("NINJA_SKIP_REGISTRY", False)
        if not skip_registry and self.urls_namespace in NinjaAPI._registry:
            msg = [
                "Looks like you created multiple NinjaAPIs",
                "To let ninja distinguish them you need to set either unique version or url_namespace",
                " - NinjaAPI(..., version='2.0.0')",
                " - NinjaAPI(..., urls_namespace='otherapi')",
                f"Already registered: {NinjaAPI._registry}",
            ]
            raise ConfigError("\n".join(msg))
        NinjaAPI._registry.append(self.urls_namespace)
