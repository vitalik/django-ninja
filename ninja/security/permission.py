from abc import ABC, abstractmethod
from typing import Any, Optional

from django.http import HttpRequest


class BasePermission(ABC):
    def __init__(self, permission: str) -> None:
        self.permission = permission

    def __call__(self, request: HttpRequest) -> Optional[Any]:
        return self.has_permission(request, self.permission)

    @abstractmethod
    def has_permission(self, request: HttpRequest, permission: str) -> Optional[Any]:
        pass  # pragma: no cover
