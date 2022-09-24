from ninja import NinjaAPI
from ninja.server import Server, ServerVariable


class TestServer:
    def test_server_basic(self):
        url = "http://example.com"
        server_1 = Server(url)
        api = NinjaAPI(servers=[server_1])
        schema = api.get_openapi_schema()

        schema_server = schema["servers"]
        assert schema_server == [{"url": url}]

    def test_server_with_description(self):
        url = "http://example.com"
        description = "this is the example server"
        server_1 = Server(url, description=description)
        api = NinjaAPI(servers=[server_1])
        schema = api.get_openapi_schema()

        schema_server = schema["servers"]
        assert schema_server == [{"url": url, "description": description}]

    def test_multiple_servers_with_description(self):
        url_1 = "http://example1.com"
        description_1 = "this is the example server"
        url_2 = "http://example2.com"
        description_2 = "this is the second example server"
        server_1 = Server(url_1, description=description_1)
        server_2 = Server(url_2, description=description_2)
        api = NinjaAPI(servers=[server_1, server_2])
        schema = api.get_openapi_schema()

        schema_server = schema["servers"]
        assert schema_server == [
            {"url": url_1, "description": description_1},
            {"url": url_2, "description": description_2},
        ]

    def test_with_parameters_simple(self):
        url = "{protocol}://example.com"
        variable_name = "protocol"
        variable_default = "https"
        variable_1 = ServerVariable(variable_name, variable_default)
        variables = [variable_1]
        server_1 = Server(url, variables=variables)
        api = NinjaAPI(servers=[server_1])
        schema = api.get_openapi_schema()

        schema_server = schema["servers"]
        assert schema_server == [
            {"url": url, "variables": {variable_name: {"default": variable_default}}}
        ]

    def test_with_parameters_and_enums(self):
        variable_name_1 = "protocol"
        variable_name_2 = "user"
        url = f"{variable_name_1}://{variable_name_2}.example.com"
        variable_default_1 = "https"
        variable_1 = ServerVariable(variable_name_1, variable_default_1)
        variable_default_2 = "readonly"
        variable_description = "selects which user page to use"
        enum_1 = "admin"
        enum_2 = "readonly"
        variable_2 = ServerVariable(
            variable_name_2,
            variable_default_2,
            enum=["admin", "readonly"],
            description=variable_description,
        )
        variables = [variable_1, variable_2]
        server_1 = Server(url, variables=variables)
        api = NinjaAPI(servers=[server_1])
        schema = api.get_openapi_schema()

        schema_server = schema["servers"]
        assert schema_server == [
            {
                "url": url,
                "variables": {
                    variable_name_1: {"default": variable_default_1},
                    variable_name_2: {
                        "default": variable_default_2,
                        "enum": [enum_1, enum_2],
                        "description": variable_description,
                    },
                },
            }
        ]
