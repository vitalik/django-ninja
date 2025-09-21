from ninja import NinjaAPI, Router


def test_openapi_info_defined():
    "Test appending schema.info"
    extra_info = {
        "termsOfService": "https://example.com/terms/",
        "title": "Test API",
    }
    api = NinjaAPI(openapi_extra={"info": extra_info}, version="1.0.0")
    schema = api.get_openapi_schema()

    assert schema["info"]["termsOfService"] == "https://example.com/terms/"
    assert schema["info"]["title"] == "Test API"
    assert schema["info"]["version"] == "1.0.0"


def test_openapi_no_additional_info():
    api = NinjaAPI(title="Test API")
    schema = api.get_openapi_schema()

    assert schema["info"]["title"] == "Test API"
    assert "termsOfService" not in schema["info"]


def test_openapi_extra():
    "Test adding extra attribute to the schema"
    api = NinjaAPI(
        openapi_extra={
            "externalDocs": {
                "description": "Find more info here",
                "url": "https://example.com",
            }
        },
        version="1.0.0",
    )
    schema = api.get_openapi_schema()

    assert schema == {
        "openapi": "3.1.0",
        "info": {"title": "NinjaAPI", "version": "1.0.0", "description": ""},
        "paths": {},
        "components": {"schemas": {}},
        "servers": [],
        "externalDocs": {
            "description": "Find more info here",
            "url": "https://example.com",
        },
    }


def test_router_openapi_extra_extends():
    """
    Test for #1505.
    When adding an extra parameter to a route via openapi_extra, this should be combined with the route's own parameters.
    """
    api = NinjaAPI()
    test_router = Router()
    api.add_router("", test_router)

    extra_param = {
        "in": "header",
        "name": "X-HelloWorld",
        "required": False,
        "schema": {
            "type": "string",
            "format": "uuid",
        },
    }

    @test_router.get("/path/{item_id}", openapi_extra={"parameters": [extra_param]})
    def get_path_item_id(request, item_id: int):
        pass

    schema = api.get_openapi_schema()

    assert len(schema["paths"]["/api/path/{item_id}"]["get"]["parameters"]) == 2
    assert schema["paths"]["/api/path/{item_id}"]["get"]["parameters"] == [
        {
            "in": "path",
            "name": "item_id",
            "required": True,
            "schema": {
                "title": "Item Id",
                "type": "integer",
            },
        },
        extra_param,
    ]
