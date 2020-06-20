class ConfigError(Exception):
    pass


class InvalidInput(Exception):
    "pydantic's ValidationError compatible"

    def __init__(self, msg, errors):
        super()
        self._errors = errors

    def errors(self):
        return self._errors


class InvalidBodyJson(InvalidInput):
    def __init__(self, msg):
        details = {
            "loc": (),  # < top level will set it to "body"
            "msg": "Invalid JSON",
            "type": "json.parse_error",
        }
        super().__init__(msg, [details])
