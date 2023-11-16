from ninja import NinjaAPI


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
