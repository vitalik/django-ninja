from ninja import NinjaAPI
import pytest

api = NinjaAPI()


class TestDecorator:
    def test_assigns_different_operation_ids_when_same_function_names(self):

        with pytest.raises(ValueError):

            @api.get("/foo")
            def operation(request):
                pass

            @api.get("/bar")
            def operation(request):
                pass
