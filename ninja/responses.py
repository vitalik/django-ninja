from pydantic import BaseModel
from django.http import JsonResponse
from django.core.serializers.json import DjangoJSONEncoder


class NinjaJSONEncoder(DjangoJSONEncoder):
    def default(self, o):
        if isinstance(o, BaseModel):
            return o.dict()
        return super().default(o)


class Response(JsonResponse):
    def __init__(self, data, **kwargs):
        super().__init__(data, encoder=NinjaJSONEncoder, safe=False, **kwargs)
