import pydantic
from typing import Callable, List
from collections import OrderedDict, namedtuple
from ninja import params
from ninja.signature.utils import get_typed_signature, get_path_param_names


FuncParam = namedtuple("FuncParam", ["name", "source", "annotation", "is_collection"])


class ViewSignature:
    def __init__(self, path: str, view_func: Callable):
        self.view_func = view_func
        self.signature = get_typed_signature(self.view_func)
        self.path_params_names = get_path_param_names(path)

        self.params = []
        for name, arg in self.signature.parameters.items():
            if name == "request":
                # TODO: maybe better assert that 1st param is request  or check by type?
                continue

            func_param = self._get_param_type(name, arg)
            self.params.append(func_param)

        self.models = self._create_models()

    def _create_models(self):
        grouping = OrderedDict()
        for param in self.params:
            d_type = type(param.source)
            if d_type not in grouping:
                grouping[d_type] = []
            grouping[d_type].append(param)

        result = []
        for cls, args in grouping.items():
            cls_name: str = cls.__name__ + "Params"
            attrs = {i.name: i.source for i in args}
            attrs["_in"] = cls._in()

            if len(args) == 1:
                if cls._in() == "body" or is_pydantic_model(args[0].annotation):
                    attrs["_single_attr"] = args[0].name

            # adding annotations:
            attrs["__annotations__"] = {i.name: i.annotation for i in args}

            # collection fields:
            attrs["_collection_fields"] = [i.name for i in args if i.is_collection]

            base_cls = cls._model
            # print([cls_name, (base_cls,), attrs])
            model_cls = type(cls_name, (base_cls,), attrs)
            # TODO: https://pydantic-docs.helpmanual.io/usage/models/#dynamic-model-creation - check if anything special in create_model method that I did not use
            result.append(model_cls)
        return result

    def _get_param_type(self, name, arg):
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

        # 1) if type of the param is defined as one of the Param's subclasses - we just use that definition
        if isinstance(arg.default, params.Param):
            param_source = arg.default

        # 2) if param name is a part of the path parameter
        elif name in self.path_params_names:
            assert arg.default == self.signature.empty, "'{name}' is a path param"
            param_source = params.Path(...)

        # 3) if param have no  type annotation or annotation is not part of pydantic model:
        elif is_collection or is_pydantic_model(annotation):
            if arg.default == self.signature.empty:
                param_source = params.Body(...)
            else:
                param_source = params.Body(arg.default)

        # 4) the last case is body param
        else:
            if arg.default == self.signature.empty:
                param_source = params.Query(...)
            else:
                param_source = params.Query(arg.default)

        return FuncParam(name, param_source, annotation, is_collection)


def is_pydantic_model(cls):
    try:
        return issubclass(cls, pydantic.BaseModel)
    except TypeError:
        return False


def is_collection_type(annotation):
    # List[int]  =>  __origin__ = list, __args__ = int
    origin = getattr(annotation, "__origin__", None)
    return origin in (List, list, set, tuple)  # TODO: I gues we should handle only list
