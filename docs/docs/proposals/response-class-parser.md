


```Python


api = NinjaAPI(response_class=Response, parser=default_parser)


api = NinjaAPI(response_class=UJSONResponse)

```




```Python

# default parser
class Parser:
    def parse_body(self, request):
        return json.loads(request.body)
    
    def querydict_to_dict(cls, request, data: QueryDict):
        list_fields = getattr(cls, "_collection_fields", [])
        result = {}
        for key in data.keys():
            if key in list_fields:
                result[key] = data.getlist(key)
            else:
                result[key] = data[key]
        return resurt


class ParserEmptyNone:

    def querydict_to_dict(cls, request, data: QueryDict):
        data = super()...
        for k in data.keys():
            if data[k] == "":
                data[k] = None


class XMLParser:
    def parse_body(self, request): # TODO: check xml parser on drf
        return xml_parse(request.body)


```



```Python


class ORJSONResponse(HttpResponse):
    def __init__(self, data, **kwargs):
        return super().__init__(orjson.dumps(data), **kwargs)

```


```Python


content_types = ContentNegotiation(
    parsers = {
        'application/json': ORJSONParser(),
        'text/xml': XMLParser(),
    },
    response_classes = {
        'application/json': Response,
        'text/xml': XMLResponse,
    },
)


api = NinjaAPI(response_class=content_types.response_class, parser=content_types.parser)



```

