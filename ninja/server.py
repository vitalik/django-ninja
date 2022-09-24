from typing import List, Optional

from ninja.types import DictStrAny

__all__ = ["Server", "ServerVariable"]


class ServerVariable:
    def __init__(
        self,
        variable: str,
        default: str,
        enum: Optional[List[str]] = None,
        description: Optional[str] = None,
    ) -> None:
        self.variable: str = variable
        self.default: str = default
        self.enum: Optional[List[str]] = enum
        self.description: Optional[str] = description

    def to_dict(self) -> DictStrAny:
        result: DictStrAny = {"default": self.default}
        if self.enum:
            result["enum"] = self.enum
        if self.description:
            result["description"] = self.description

        return result


class Server:
    def __init__(
        self,
        url: str = "/",
        description: Optional[str] = None,
        variables: Optional[List[ServerVariable]] = None,
    ) -> None:
        self.description = description
        self.url = url
        self.variables = variables

    def to_dict(self) -> DictStrAny:
        result: DictStrAny = {"url": self.url}
        if self.description:
            result["description"] = self.description
        if self.variables:
            result["variables"] = {
                variable.variable: variable.to_dict() for variable in self.variables
            }

        return result
