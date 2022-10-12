from collections import OrderedDict
from decimal import Decimal

# automatically imports fast C version if available
from yaml import SafeDumper

from ninja.openapi.schema import OpenAPISchema


class NinjaSafeDumper(SafeDumper):
    def represent_decimal(self, data):
        return self.represent_scalar("tag:yaml.org,2002:str", str(data))

    def represent_ordered_dict(self, data):
        return self.represent_mapping("tag:yaml.org,2002:map", data.items())

    def represent_openapi_schema(self, data):
        # TODO: deal with sort_keys? how does it relate to represent_ordered_dict?
        return self.represent_dict(dict(data))


NinjaSafeDumper.add_representer(OpenAPISchema, NinjaSafeDumper.represent_openapi_schema)
NinjaSafeDumper.add_representer(Decimal, NinjaSafeDumper.represent_decimal)
NinjaSafeDumper.add_representer(OrderedDict, NinjaSafeDumper.represent_ordered_dict)
