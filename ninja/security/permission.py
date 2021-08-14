from abc import ABC, abstractmethod
from typing import Any, Optional

from django.http import HttpRequest


class BasePermission(ABC):
    @abstractmethod
    def has_permission(self, request: HttpRequest, permission: str) -> Optional[Any]:
        pass  # pragma: no cover
