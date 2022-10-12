from collections import OrderedDict
from decimal import Decimal
from typing import IO, Mapping, Optional, Tuple

from ninja.openapi.schema import OpenAPISchema

try:
    import yaml as yaml
except ImportError:
    raise ModuleNotFoundError("Install PyYAML or django-ninja[yaml].")


class NinjaSafeDumper(yaml.SafeDumper):
    def __init__(
        self,
        stream: IO,
        default_style: Optional[str] = None,
        default_flow_style: Optional[bool] = None,
        canonical: Optional[bool] = None,
        indent: Optional[int] = None,
        width: Optional[int] = None,
        allow_unicode: Optional[bool] = None,
        line_break: Optional[str] = None,
        encoding: Optional[str] = None,
        explicit_start: Optional[bool] = None,
        explicit_end: Optional[bool] = None,
        version: Optional[Tuple[int, int]] = None,
        tags: Optional[Mapping[str, str]] = None,
        sort_keys: bool = False,
    ) -> None:
        # note that `sort_keys` is `False` by default, to align better with the `sort_keys` option in
        # `export_openapi_schema`. this is different from PyYAML's default.
        super().__init__(
            stream,
            default_style,
            default_flow_style,
            canonical,
            indent,
            width,
            allow_unicode,
            line_break,
            encoding,
            explicit_start,
            explicit_end,
            version,
            tags,
            sort_keys,
        )


def represent_decimal(dumper: NinjaSafeDumper, data: Decimal) -> yaml.ScalarNode:
    return dumper.represent_scalar("tag:yaml.org,2002:str", str(data.normalize()))


def represent_ordered_dict(
    dumper: NinjaSafeDumper, data: OrderedDict
) -> yaml.MappingNode:
    # just use the same yaml representation as regular dicts. in yaml, they're
    # usually represented by the same tag, and since python 3.7, the language
    # specification for dict requires that insertion order is kept.
    return dumper.represent_dict(data)


def represent_openapi_schema(
    dumper: NinjaSafeDumper, data: OpenAPISchema
) -> yaml.MappingNode:
    return dumper.represent_dict(data)


NinjaSafeDumper.add_representer(Decimal, represent_decimal)
NinjaSafeDumper.add_representer(OrderedDict, represent_ordered_dict)
NinjaSafeDumper.add_representer(OpenAPISchema, represent_openapi_schema)
