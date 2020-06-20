from ninja.errors import ConfigError


class SecuritySchema(dict):
    def __init__(self, type: str, **kwargs):
        super().__init__(type=type, **kwargs)


class AuthBase:
    def __init__(self):
        if not hasattr(self, "openapi_type"):
            raise ConfigError("If you extend AuthBase you need to define openapi_type")

        kwargs = {}
        for attr in dir(self):
            if attr.startswith("openapi_"):
                name = attr.replace("openapi_", "", 1)
                kwargs[name] = getattr(self, attr)
        self.openapi_securty_schema = SecuritySchema(**kwargs)

    def __call__(self, request):
        raise NotImplementedError("Please implement call")
