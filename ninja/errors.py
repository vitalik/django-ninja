class ConfigError(Exception):
    pass


class InvalidInput(Exception):
    "pydantic's ValidationError compatible error"

    def __init__(self, msg, errors):
        super()  # TODO: ? no __init__ ?
        self._errors = errors

    def errors(self):
        return self._errors


class InvalidBody(InvalidInput):
    def __init__(self, msg):
        details = {
            "loc": (),  # < top level will set it to "body"
            "msg": "Cannot parse request body",
            "type": "parse_error",
        }
        super().__init__(msg, [details])
