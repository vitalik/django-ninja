from ninja import NinjaAPI


class TestServer:
    def test_server_basic(self):
        server = {"url": "http://example.com"}
        api = NinjaAPI(servers=[server])
        schema = api.get_openapi_schema()

        schema_server = schema["servers"]
        assert schema_server == [server]

    def test_server_with_description(self):
        server = {
            "url": "http://example.com",
            "description": "this is the example server",
        }
        api = NinjaAPI(servers=[server])
        schema = api.get_openapi_schema()

        schema_server = schema["servers"]
        assert schema_server == [server]

    def test_multiple_servers_with_description(self):
        server_1 = {
            "url": "http://example1.com",
            "description": "this is the example server 1",
        }
        server_2 = {
            "url": "http://example2.com",
            "description": "this is the example server 2",
        }
        servers = [server_1, server_2]
        api = NinjaAPI(servers=servers)
        schema = api.get_openapi_schema()

        schema_server = schema["servers"]
        assert schema_server == servers
