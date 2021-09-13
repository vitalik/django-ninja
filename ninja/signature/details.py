import inspect
from collections import defaultdict, namedtuple
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional

import pydantic

from ninja import UploadedFile, params
from ninja.compatibility.util import get_origin as get_collection_origin
from ninja.errors import ConfigError
from ninja.params import File
from ninja.params_models import TModels
from ninja.signature.utils import get_path_param_names, get_typed_signature

if TYPE_CHECKING:
    from pydantic.fields import ModelField  # pragma: no cover


__all__ = [
    "ViewSignature",
    "is_pydantic_model",
    "is_collection_type",
    "detect_collection_fields",
]

FuncParam = namedtuple("FuncParam", ["name", "source", "annotation", "is_collection"])


class ViewSignature:
    def __init__(self, path: str, view_func: Callable) -> None:
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

            func_param = self._get_param_type(name, arg)
            self.params.append(func_param)

        if hasattr(view_func, "_ninja_contribute_args"):
            # _ninja_contribute_args is a special attribute
            # which allows developers to create custom function params
            # inside decorators or other functions
            for p_name, p_type, p_source in view_func._ninja_contribute_args:  # type: ignore
                self.params.append(FuncParam(p_name, p_source, p_type, False))

        self.models: TModels = self._create_models()

    def _create_models(self) -> TModels:
        params_by_source_cls: Dict[Any, List[FuncParam]] = defaultdict(list)
        for param in self.params:
            param_source_cls = type(param.source)
            params_by_source_cls[param_source_cls].append(param)

        result = []
        for param_cls, args in params_by_source_cls.items():
            cls_name: str = param_cls.__name__ + "Params"
            attrs = {i.name: i.source for i in args}
            attrs["_param_source"] = param_cls._param_source()

            if len(args) == 1:
                if attrs["_param_source"] == "body" or is_pydantic_model(
                    args[0].annotation
                ):
                    attrs["_single_attr"] = args[0].name

            elif attrs["_param_source"] == "file":
                # More than one File() is not allowed
                func_name = getattr(self.view_func, "__name__", "<UNKNOWN>")
                names = ", ".join(arg.name for arg in args)
                raise ConfigError(
                    f"Only 1 '{param_cls.__name__}()' param allowed for path:{self.path} function:"
                    f"{func_name} found: {names}. Try type: 'List[UploadedFile]'"
                )
            else:
                # combine multiple models (mixed attrs)
                pydantic_models = [
                    arg for arg in args if is_pydantic_model(arg.annotation)
                ]
                if pydantic_models:
                    mixed_attrs = {}
                    for modeled_attr in pydantic_models:
                        for (
                            attr_name,
                            field,
                        ) in modeled_attr.annotation.__fields__.items():
                            mixed_attrs[attr_name] = modeled_attr.name
                            mixed_attrs[field.alias] = modeled_attr.name

                    attrs["_mixed_attrs"] = mixed_attrs

            # adding annotations:
            attrs["__annotations__"] = {i.name: i.annotation for i in args}

            # collection fields:
            attrs["_collection_fields"] = detect_collection_fields(args)

            base_cls = param_cls._model
            model_cls = type(cls_name, (base_cls,), attrs)
            # TODO: https://pydantic-docs.helpmanual.io/usage/models/#dynamic-model-creation - check if anything special in create_model method that I did not use
            result.append(model_cls)
        return result

    def _get_param_type(self, name: str, arg: inspect.Parameter) -> FuncParam:
        # _EMPTY = self.signature.empty
        annotation = arg.annotation

        if annotation == self.signature.empty:
            if arg.default == self.signature.empty:
                annotation = str
            else:
                if isinstance(arg.default, params.Param):
                    annotation = type(arg.default.default)
                else:
                    annotation = type(arg.default)

        if annotation == type(None) or annotation == type(Ellipsis):  # noqa
            annotation = str

        is_collection = is_collection_type(annotation)

        if annotation == UploadedFile or (
            is_collection and annotation.__args__[0] == UploadedFile
        ):
            # People often forgot to mark UploadedFile as a File, so we better assign it automatically
            if arg.default == self.signature.empty or arg.default is None:
                default = arg.default == self.signature.empty and ... or arg.default
                return FuncParam(name, File(default), annotation, is_collection)

        # 1) if type of the param is defined as one of the Param's subclasses - we just use that definition
        if isinstance(arg.default, params.Param):
            param_source = arg.default

        # 2) if param name is a part of the path parameter
        elif name in self.path_params_names:
            assert (
                arg.default == self.signature.empty
            ), f"'{name}' is a path param, default not allowed"
            param_source = params.Path(...)

        # 3) if param is a collection, or annotation is part of pydantic model:
        elif is_collection or is_pydantic_model(annotation):
            if arg.default == self.signature.empty:
                param_source = params.Body(...)
            else:
                param_source = params.Body(arg.default)

        # 4) the last case is query param
        else:
            if arg.default == self.signature.empty:
                param_source = params.Query(...)
            else:
                param_source = params.Query(arg.default)

        return FuncParam(name, param_source, annotation, is_collection)


def is_pydantic_model(cls: Any) -> bool:
    try:
        return issubclass(cls, pydantic.BaseModel)
    except TypeError:
        return False


def is_collection_type(annotation: Any) -> bool:
    origin = get_collection_origin(annotation)
    return origin in (
        List,
        list,
        set,
        tuple,
    )  # TODO: I guess we should handle only list


def detect_pydantic_model_collection_fields(model: pydantic.BaseModel) -> List[str]:
    "Extracts collection fields aliases from collection fields"

    def _list_field_name(field: "ModelField") -> Optional[str]:
        if is_collection_type(field.outer_type_):
            return str(field.alias)
        return None

    return list(filter(None, map(_list_field_name, model.__fields__.values())))


def detect_collection_fields(args: List[FuncParam]) -> List[str]:
    """
    QueryDict has values that are always lists, so we need to help django ninja to understand
    better the input parameters if it's a list or a single value
    This method detects attributes that should be treated by ninja as lists and returns this list as a result
    """
    result = [i.name for i in args if i.is_collection]

    if len(args) == 1 and is_pydantic_model(args[0].annotation):
        result += detect_pydantic_model_collection_fields(args[0].annotation)

    return result
