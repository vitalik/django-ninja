from typing import TYPE_CHECKING, Any, Callable, Dict, Optional, TypeVar

from typing_extensions import Annotated

from ninja.params import functions as param_functions

__all__ = [
    "Body",
    "Cookie",
    "File",
    "Form",
    "Header",
    "Path",
    "Query",
    "BodyEx",
    "CookieEx",
    "FileEx",
    "FormEx",
    "HeaderEx",
    "PathEx",
    "QueryEx",
    "Router",
    "P",
]


class ParamShortcut:
    def __init__(self, base_func: Callable) -> None:
        self._base_func = base_func

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        return self._base_func(*args, **kwargs)

    def __getitem__(self, args: Any) -> Any:
        if isinstance(args, tuple):
            return Annotated[args[0], self._base_func(**args[1])]
        return Annotated[args, self._base_func()]


if TYPE_CHECKING:  # pragma: nocover
    # mypy cheats
    T = TypeVar("T")
    Body = Annotated[T, param_functions.Body()]
    Cookie = Annotated[T, param_functions.Cookie()]
    File = Annotated[T, param_functions.File()]
    Form = Annotated[T, param_functions.Form()]
    Header = Annotated[T, param_functions.Header()]
    Path = Annotated[T, param_functions.Path()]
    Query = Annotated[T, param_functions.Query()]
    # mypy does not like to extend already annotated params
    # with extra annotation (so need to cheat with these XXX-Ex types):
    from typing_extensions import Annotated as BodyEx
    from typing_extensions import Annotated as CookieEx
    from typing_extensions import Annotated as FileEx
    from typing_extensions import Annotated as FormEx
    from typing_extensions import Annotated as HeaderEx
    from typing_extensions import Annotated as PathEx
    from typing_extensions import Annotated as QueryEx
else:
    Body = ParamShortcut(param_functions.Body)
    Cookie = ParamShortcut(param_functions.Cookie)
    File = ParamShortcut(param_functions.File)
    Form = ParamShortcut(param_functions.Form)
    Header = ParamShortcut(param_functions.Header)
    Path = ParamShortcut(param_functions.Path)
    Query = ParamShortcut(param_functions.Query)
    # mypy does not like to extend already annotated params
    # with extra annotation (so need to cheat with these XXX-Ex types):
    BodyEx = Body
    CookieEx = Cookie
    FileEx = File
    FormEx = Form
    HeaderEx = Header
    PathEx = Path
    QueryEx = Query


def P(
    *,
    alias: Optional[str] = None,
    title: Optional[str] = None,
    description: Optional[str] = None,
    gt: Optional[float] = None,
    ge: Optional[float] = None,
    lt: Optional[float] = None,
    le: Optional[float] = None,
    min_length: Optional[int] = None,
    max_length: Optional[int] = None,
    regex: Optional[str] = None,
    example: Any = None,
    examples: Optional[Dict[str, Any]] = None,
    deprecated: Optional[bool] = None,
    include_in_schema: bool = True,
    **extra: Any,
) -> Dict[str, Any]:
    "Arguments for BodyEx, QueryEx, etc."
    return dict(
        alias=alias,
        title=title,
        description=description,
        gt=gt,
        ge=ge,
        lt=lt,
        le=le,
        min_length=min_length,
        max_length=max_length,
        regex=regex,
        example=example,
        examples=examples,
        deprecated=deprecated,
        include_in_schema=include_in_schema,
        **extra,
    )
