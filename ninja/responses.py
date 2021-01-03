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


def resp_codes(from_code: int, to_code: int) -> frozenset:
    return frozenset(range(from_code, to_code + 1))


# most common http status codes
codes_1xx = resp_codes(100, 101)
codes_2xx = resp_codes(200, 206)
codes_3xx = resp_codes(300, 308)
codes_4xx = resp_codes(400, 412) | frozenset({416, 418, 425, 429, 451})
codes_5xx = resp_codes(500, 504)
