from typing import Callable

import django
from django.http import HttpRequest

try:
    from django.utils.datastructures import CaseInsensitiveMapping
except ImportError:
    from .datastructures import CaseInsensitiveMapping


# HttpHeaders copypasted from django 3.0 codebase
class HttpHeaders(CaseInsensitiveMapping):
    HTTP_PREFIX = "HTTP_"
    # PEP 333 gives two headers which aren't prepended with HTTP_.
    UNPREFIXED_HEADERS = {"CONTENT_TYPE", "CONTENT_LENGTH"}

    def __init__(self, environ):
        headers = {}
        for header, value in environ.items():
            name = self.parse_header_name(header)
            if name:
                headers[name] = value
        super().__init__(headers)

    def __getitem__(self, key):
        """Allow header lookup using underscores in place of hyphens."""
        return super().__getitem__(key.replace("_", "-"))

    @classmethod
    def parse_header_name(cls, header):
        if header.startswith(cls.HTTP_PREFIX):
            start = len(cls.HTTP_PREFIX)
            header = header[start:]
        elif header not in cls.UNPREFIXED_HEADERS:
            return None
        return header.replace("_", "-").title()


def get_headers_old(request):
    return HttpHeaders(request.META)


def get_headers_v3(request):
    return request.headers


get_headers: Callable[[HttpRequest], HttpHeaders]

if django.VERSION[0] < 3:
    get_headers = get_headers_old
else:
    get_headers = get_headers_v3
