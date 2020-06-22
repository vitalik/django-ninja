import pydantic
from typing import Callable, List, Any, Union, Optional, Sequence
from django.http import HttpResponse
from ninja.responses import Response
from ninja.errors import InvalidInput
from ninja.constants import NOT_SET
from ninja.signature import ViewSignature


class Operation:
    def __init__(
        self,
        path: str,
        methods: List[str],
        view_func: Callable,
        *,
        auth: Optional[Union[Sequence[Callable], Callable, object]] = NOT_SET
    ):
        self.path = path
        self.methods = methods
        self.view_func = view_func
        self.auth: Sequence[Callable] = []
        if auth is not None and auth is not NOT_SET:
            self.auth = isinstance(auth, Sequence) and auth or [auth]

        self.signature = ViewSignature(self.path, self.view_func)
        self.models = self.signature.models
        self.response_model = self.signature.response_model

    def run(self, request, **kw):
        unauthorized = self._run_authentication(request)
        if unauthorized:
            return unauthorized

        values, errors = self._get_values(request, kw)
        if errors:
            return Response({"detail": errors}, status=422)
        result = self.view_func(request, **values)
        return self._create_response(result)

    def _run_authentication(self, request):
        if not self.auth:
            return
        for callback in self.auth:
            result = callback(request)
            if result is not None:
                request.auth = result
                return
        return Response({"detail": "Unauthorized"}, status=401)

    def _create_response(self, result: Any):
        if isinstance(result, HttpResponse):
            return result
        if self.response_model is None:
            return Response(result)

        result = self.response_model(response=result).dict()["response"]
        return Response(result)

    def _get_values(self, request, path_params):
        values, errors = {}, []
        for model in self.models:
            try:
                data = model.resolve(request, path_params)
                values.update(data)
            except (pydantic.ValidationError, InvalidInput) as e:
                items = []
                for i in e.errors():
                    i["loc"] = (model._in,) + i["loc"]
                    items.append(i)
                errors.extend(items)
        return values, errors


# TODO: AsyncOperation ?
