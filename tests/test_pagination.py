from ninja import NinjaAPI, Schema
from ninja.pagination import PageNumberPagination, PaginationBase, paginate
from ninja.testing import TestClient

api = NinjaAPI()


ITEMS = list(range(100))


class CustomPagination(PaginationBase):
    # only offset param, defaults to 5 per page
    class Input(Schema):
        skip: int

    def paginate_queryset(self, items, **params):
        skip = params[self.name_param].skip
        return items[skip : skip + 5]


@api.get("/items_1")
@paginate  # WITHOUT brackets (should use default pagination)
def items_1(request, **kwargs):
    return ITEMS


@api.get("/items_2")
@paginate()  # with brackets (should use default pagination)
def items_2(request, someparam: int = 0, **kwargs):
    # also having custom param `someparam` - that should not be lost
    return ITEMS


@api.get("/items_3")
@paginate(CustomPagination)
def items_3(request, **kwargs):
    return ITEMS


@api.get("/items_4")
@paginate(PageNumberPagination, page_size=10)
def items_4(request, **kwargs):
    return ITEMS


@api.get("/items_5")
@paginate(PageNumberPagination, page_size=10)
def items_5(request):
    return ITEMS


@api.get("/items_6")
@paginate(PageNumberPagination, page_size=10, pass_parameter="page_info")
def items_6(request, **kwargs):
    return ITEMS + [kwargs["page_info"].page]


client = TestClient(api)


def test_case1():
    response = client.get("/items_1?limit=10").json()
    assert response == ITEMS[:10]

    schema = api.get_openapi_schema()["paths"]["/api/items_1"]["get"]
    # print(schema)
    assert schema["parameters"] == [
        {
            "in": "query",
            "name": "limit",
            "schema": {
                "title": "Limit",
                "default": 100,
                "exclusiveMinimum": 0,
                "type": "integer",
            },
            "required": False,
        },
        {
            "in": "query",
            "name": "offset",
            "schema": {
                "title": "Offset",
                "default": 0,
                "exclusiveMinimum": -1,
                "type": "integer",
            },
            "required": False,
        },
    ]


def test_case2():
    response = client.get("/items_2?limit=10").json()
    assert response == ITEMS[:10]

    schema = api.get_openapi_schema()["paths"]["/api/items_2"]["get"]
    print(schema["parameters"])
    assert schema["parameters"] == [
        {
            "in": "query",
            "name": "someparam",
            "schema": {"title": "Someparam", "default": 0, "type": "integer"},
            "required": False,
        },
        {
            "in": "query",
            "name": "limit",
            "schema": {
                "title": "Limit",
                "default": 100,
                "exclusiveMinimum": 0,
                "type": "integer",
            },
            "required": False,
        },
        {
            "in": "query",
            "name": "offset",
            "schema": {
                "title": "Offset",
                "default": 0,
                "exclusiveMinimum": -1,
                "type": "integer",
            },
            "required": False,
        },
    ]


def test_case3():
    response = client.get("/items_3?skip=5").json()
    assert response == ITEMS[5:10]

    schema = api.get_openapi_schema()["paths"]["/api/items_3"]["get"]
    print(schema)
    assert schema["parameters"] == [
        {
            "in": "query",
            "name": "skip",
            "schema": {"title": "Skip", "type": "integer"},
            "required": True,
        }
    ]


def test_case4():
    response = client.get("/items_4?page=2").json()
    assert response == ITEMS[10:20]

    schema = api.get_openapi_schema()["paths"]["/api/items_4"]["get"]
    # print(schema)
    assert schema["parameters"] == [
        {
            "in": "query",
            "name": "page",
            "schema": {
                "title": "Page",
                "default": 1,
                "exclusiveMinimum": 0,
                "type": "integer",
            },
            "required": False,
        }
    ]


def test_case5_no_kwargs():
    response = client.get("/items_5?page=2").json()
    assert response == ITEMS[10:20]

    schema = api.get_openapi_schema()["paths"]["/api/items_5"]["get"]

    assert schema["parameters"] == [
        {
            "in": "query",
            "name": "page",
            "schema": {
                "title": "Page",
                "default": 1,
                "exclusiveMinimum": 0,
                "type": "integer",
            },
            "required": False,
        }
    ]


def test_case6_pass_param_kwargs():
    page = 11
    response = client.get(f"/items_6?page={page}").json()
    assert response == [page], response

    schema = api.get_openapi_schema()["paths"]["/api/items_6"]["get"]

    assert schema["parameters"] == [
        {
            "in": "query",
            "name": "page",
            "schema": {
                "title": "Page",
                "default": 1,
                "exclusiveMinimum": 0,
                "type": "integer",
            },
            "required": False,
        }
    ]
