from ninja import NinjaAPI


class TestOpenAPIInfo:
    def test_openapi_info_defined(self):
        openapi_info = {
            "termsOfService": "https://example.com/terms/",
            "title": "Test API"
        }
        api = NinjaAPI(openapi_info=openapi_info, version="1.0.0")
        schema = api.get_openapi_schema()

        assert schema["info"]["termsOfService"] == "https://example.com/terms/"
        assert schema["info"]["title"] == "Test API"
        assert schema["info"]["version"] == "1.0.0"

    def test_openapi_no_additional_info(self):
        api = NinjaAPI(title="Test API")
        schema = api.get_openapi_schema()

        assert schema["info"]["title"] == "Test API"
        assert "termsOfService" not in schema["info"]
