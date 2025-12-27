from typing import Any, Optional
from django.http import HttpRequest, HttpResponse

class ResponseFactory:
    def __init__(self, renderer):
        self.renderer = renderer

    def create_response(
        self,
        request: HttpRequest,
        data: Any,
        *,
        status: int,
        temporal_response: Optional[HttpResponse] = None,
    ) -> HttpResponse:
        content = self.renderer.render(request, data, response_status=status)
        if temporal_response:
            temporal_response.content = content
            return temporal_response
        return HttpResponse(content, status=status, content_type=self.get_content_type())

    def create_temporal_response(self) -> HttpResponse:
        return HttpResponse("", content_type=self.get_content_type())

    def get_content_type(self) -> str:
        return f"{self.renderer.media_type}; charset={self.renderer.charset}"
