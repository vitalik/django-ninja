import inspect
import warnings
from collections import defaultdict, namedtuple
from typing import Any, Callable, Dict, Generator, List, Optional, Tuple

import pydantic
from django.http import HttpResponse
from pydantic.fields import FieldInfo
from pydantic_core import PydanticUndefined
from typing_extensions import Annotated, get_args, get_origin

from ninja import UploadedFile
from ninja.compatibility.util import UNION_TYPES
from ninja.errors import ConfigError
from ninja.params.models import (
    Body,
    File,
    Form,
    Param,
    Path,
    Query,
    TModel,
    TModels,
    _MultiPartBody,
)
from ninja.signature.utils import get_path_param_names, get_typed_signature

__all__ = [
    "ViewSignature",
    "is_pydantic_model",
    "is_collection_type",
    "detect_collection_fields",
]

FuncParam = namedtuple(
    "FuncParam", ["name", "alias", "source", "annotation", "is_collection"]
)


class ViewSignature:
    FLATTEN_PATH_SEP = (
        "\x1e"  # ASCII Record Separator.  IE: not generally used in query names
    )
    response_arg: Optional[str] = None

    def __init__(self, path: str, view_func: Callable[..., Any]) -> None:
        self.view_func = view_func
        self.signature = get_typed_signature(self.view_func)
        self.path = path
        self.path_params_names = get_path_param_names(path)
        self.docstring = inspect.cleandoc(view_func.__doc__ or "")
        self.has_kwargs = False

        self.params = []
        for name, arg in self.signature.parameters.items():
            if name == "request":
                # TODO: maybe better assert that 1st param is request or check by type?
                # maybe even have attribute like `has_request`
                # so that users can ignore passing request if not needed
                continue

            if arg.kind == arg.VAR_KEYWORD:
                # Skipping **kwargs
                self.has_kwargs = True
                continue

            if arg.kind == arg.VAR_POSITIONAL:
                # Skipping *args
                continue

            if arg.annotation is HttpResponse:
                self.response_arg = name
                continue

            if (
                arg.annotation is inspect.Parameter.empty
                and isinstance(arg.default, type)
                and issubclass(arg.default, pydantic.BaseModel)
            ):
                raise ConfigError(
                    f"Looks like you are using `{name}={arg.default.__name__}` instead of `{name}: {arg.default.__name__}` (annotation)"
                )

            func_param = self._get_param_type(name, arg)
            self.params.append(func_param)

        if hasattr(view_func, "_ninja_contribute_args"):
            # _ninja_contribute_args is a special attribute
            # which allows developers to create custom function params
            # inside decorators or other functions
            for p_name, p_type, p_source in view_func._ninja_contribute_args:
                self.params.append(
                    FuncParam(p_name, p_source.alias or p_name, p_source, p_type, False)
                )

        self.models: TModels = self._create_models()

        self._validate_view_path_params()

    def _validate_view_path_params(self) -> None:
        """verify all path params are present in the path model fields"""
        if self.path_params_names:
            path_model = next(
                (m for m in self.models if m.__ninja_param_source__ == "path"), None
            )
            missing = tuple(
                sorted(
                    name
                    for name in self.path_params_names
                    if not (path_model and name in path_model.__ninja_flatten_map__)
                )
            )
            if missing:
                warnings.warn_explicit(
                    UserWarning(
                        f"Field(s) {missing} are in the view path, but were not found in the view signature."
                    ),
                    category=None,
                    filename=inspect.getfile(self.view_func),
                    lineno=inspect.getsourcelines(self.view_func)[1],
                    source=None,
                )

    def _create_models(self) -> TModels:
        params_by_source_cls: Dict[Any, List[FuncParam]] = defaultdict(list)
        for param in self.params:
            param_source_cls = type(param.source)
            params_by_source_cls[param_source_cls].append(param)

        is_multipart_response_with_body = Body in params_by_source_cls and (
            File in params_by_source_cls or Form in params_by_source_cls
        )
        if is_multipart_response_with_body:
            params_by_source_cls[_MultiPartBody] = params_by_source_cls.pop(Body)

        result = []
        for param_cls, args in params_by_source_cls.items():
            cls_name: str = param_cls.__name__ + "Params"
            attrs = {i.name: i.source for i in args}
            attrs["__ninja_param_source__"] = param_cls._param_source()
            attrs["__ninja_flatten_map_reverse__"] = {}

            if attrs["__ninja_param_source__"] == "file":
                pass

            elif attrs["__ninja_param_source__"] in {
                "form",
                "query",
                "header",
                "cookie",
                "path",
            }:
                flatten_map = self._args_flatten_map(args)
                attrs["__ninja_flatten_map__"] = flatten_map
                attrs["__ninja_flatten_map_reverse__"] = {
                    v: (k,) for k, v in flatten_map.items()
                }

            else:
                assert attrs["__ninja_param_source__"] == "body"
                if is_multipart_response_with_body:
                    attrs["__ninja_body_params__"] = {
                        i.alias: i.annotation for i in args
                    }
                else:
                    # ::TODO:: this is still sus.  build some test cases
                    attrs["__read_from_single_attr__"] = (
                        args[0].name if len(args) == 1 else None
                    )

            # adding annotations
            attrs["__annotations__"] = {i.name: i.annotation for i in args}

            # collection fields:
            attrs["__ninja_collection_fields__"] = detect_collection_fields(
                args, attrs.get("__ninja_flatten_map__", {})
            )

            base_cls = param_cls._model
            model_cls = type(cls_name, (base_cls,), attrs)
            # TODO: https://pydantic-docs.helpmanual.io/usage/models/#dynamic-model-creation - check if anything special in create_model method that I did not use
            result.append(model_cls)
        return result

    def _args_flatten_map(self, args: List[FuncParam]) -> Dict[str, Tuple[str, ...]]:
        flatten_map = {}
        arg_names: Any = {}
        for arg in args:
            if is_pydantic_model(arg.annotation):
                for name, path in self._model_flatten_map(arg.annotation, arg.alias):
                    if name in flatten_map:
                        raise ConfigError(
                            f"Duplicated name: '{name}' in params: '{arg_names[name]}' & '{arg.name}'"
                        )
                    flatten_map[name] = tuple(path.split(self.FLATTEN_PATH_SEP))
                    arg_names[name] = arg.name
            else:
                name = arg.alias
                if name in flatten_map:
                    raise ConfigError(
                        f"Duplicated name: '{name}' also in '{arg_names[name]}'"
                    )
                flatten_map[name] = (name,)
                arg_names[name] = name

        return flatten_map

    def _model_flatten_map(self, model: TModel, prefix: str) -> Generator:
        field: FieldInfo
        for attr, field in model.model_fields.items():
            field_name = field.alias or attr
            name = f"{prefix}{self.FLATTEN_PATH_SEP}{field_name}"
            if is_pydantic_model(field.annotation):
                yield from self._model_flatten_map(field.annotation, name)  # type: ignore
            else:
                yield field_name, name

    def _get_param_type(self, name: str, arg: inspect.Parameter) -> FuncParam:
        # _EMPTY = self.signature.empty
        annotation = arg.annotation
        default = arg.default

        if get_origin(annotation) is Annotated:
            args = get_args(annotation)
            if isinstance(args[1], Param):
                prev_default = default
                annotation, default = args
                if prev_default != self.signature.empty:
                    default.default = prev_default

        if annotation == self.signature.empty:
            if default == self.signature.empty:
                annotation = str
            else:
                if isinstance(default, Param):
                    annotation = type(default.default)
                else:
                    annotation = type(default)

            if annotation == PydanticUndefined.__class__:
                # TODO: ^ check why is that so
                annotation = str

        if annotation == type(None) or annotation == type(Ellipsis):  # noqa
            annotation = str

        is_collection = is_collection_type(annotation)

        if annotation == UploadedFile or (
            is_collection and annotation.__args__[0] == UploadedFile
        ):
            # People often forgot to mark UploadedFile as a File, so we better assign it automatically
            if default == self.signature.empty or default is None:
                default = default == self.signature.empty and ... or default
                return FuncParam(name, name, File(default), annotation, is_collection)

        # 1) if type of the param is defined as one of the Param's subclasses - we just use that definition
        if isinstance(default, Param):
            param_source = default

        # 2) if param name is a part of the path parameter
        elif name in self.path_params_names:
            assert (
                default == self.signature.empty
            ), f"'{name}' is a path param, default not allowed"
            param_source = Path(...)

        # 3) if param is a collection, or annotation is part of pydantic model:
        elif is_collection or is_pydantic_model(annotation):
            if default == self.signature.empty:
                param_source = Body(...)
            else:
                param_source = Body(default)

        # 4) the last case is query param
        else:
            if default == self.signature.empty:
                param_source = Query(...)
            else:
                param_source = Query(default)

        return FuncParam(
            name, param_source.alias or name, param_source, annotation, is_collection
        )


def is_pydantic_model(cls: Any) -> bool:
    try:
        origin = get_origin(cls)

        # Handle Annotated types - extract the actual type
        if origin is Annotated:
            args = get_args(cls)
            return is_pydantic_model(args[0])

        # Handle Union types
        if origin in UNION_TYPES:
            return any(issubclass(arg, pydantic.BaseModel) for arg in get_args(cls))
        return issubclass(cls, pydantic.BaseModel)
    except TypeError:  # pragma: no cover
        return False


def is_collection_type(annotation: Any) -> bool:
    origin = get_origin(annotation)

    if origin in UNION_TYPES:
        for arg in get_args(annotation):
            if is_collection_type(arg):
                return True
        return False

    collection_types = (List, list, set, tuple)
    if origin is None:
        return (
            isinstance(annotation, collection_types)
            if not isinstance(annotation, type)
            else issubclass(annotation, collection_types)
        )
    else:
        return origin in collection_types  # TODO: I guess we should handle only list


def detect_collection_fields(
    args: List[FuncParam], flatten_map: Dict[str, Tuple[str, ...]]
) -> List[str]:
    """
    Django QueryDict has values that are always lists, so we need to help django ninja to understand
    better the input parameters if it's a list or a single value
    This method detects attributes that should be treated by ninja as lists and returns this list as a result
    """
    result = [i.alias or i.name for i in args if i.is_collection]

    if flatten_map:
        args_d = {arg.alias: arg for arg in args}
        for path in (p for p in flatten_map.values() if len(p) > 1):
            annotation_or_field: Any = args_d[path[0]].annotation
            for attr in path[1:]:
                if hasattr(annotation_or_field, "annotation"):
                    annotation_or_field = annotation_or_field.annotation
                annotation_or_field = next(
                    (
                        a
                        for a in annotation_or_field.model_fields.values()
                        if a.alias == attr
                    ),
                    annotation_or_field.model_fields.get(attr),
                )  # pragma: no cover

                annotation_or_field = getattr(
                    annotation_or_field, "outer_type_", annotation_or_field
                )

            # if hasattr(annotation_or_field, "annotation"):
            annotation_or_field = annotation_or_field.annotation

            if is_collection_type(annotation_or_field):
                result.append(path[-1])
    return result
