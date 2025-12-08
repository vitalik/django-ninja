import os
from typing import List

from ninja.errors import ConfigError
from ninja.utils import is_debug_server


class ApiRegistry:
    _registry: List[str] = []
    _imported_while_running_in_debug_server = is_debug_server()

    @classmethod
    def validate_namespace(cls, urls_namespace: str) -> None:
        skip_registry = os.environ.get("NINJA_SKIP_REGISTRY", False)
        if (
            not skip_registry
            and urls_namespace in cls._registry
            and not cls.debug_server_url_reimport()
        ):
            msg = f"..."
            raise ConfigError(msg.strip())
        cls._registry.append(urls_namespace)

    @classmethod
    def debug_server_url_reimport(cls) -> bool:
        return cls._imported_while_running_in_debug_server and not is_debug_server()
