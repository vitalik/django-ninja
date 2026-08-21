import pytest
from django.db.models import QuerySet

from ninja import NinjaAPI, OrderingSchema, Query
from ninja.ordering_schema import OrderingBaseSchema
from ninja.testing import TestClient


class FakeQS(QuerySet):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.is_ordered = False

    def order_by(self, *args, **kwargs):
        self.is_ordered = True
        self.order_by_args = args
        self.order_by_kwargs = kwargs
        return self


def test_validate_order_by_field__should_pass_when_all_field_allowed():
    test_field = "test_field"

    class DummyOrderingSchema(OrderingSchema):
        pass

    order_by_value = [test_field]
    validation_result = DummyOrderingSchema.validate_order_by_field(order_by_value)
    assert validation_result == order_by_value


def test_validate_order_by_field__should_pass_when_value_in_allowed_fields_and_asc():
    test_field = "test_field"

    class DummyOrderingSchema(OrderingSchema):
        class Meta(OrderingSchema.Meta):
            allowed_fields = [test_field]

    order_by_value = [test_field]
    validation_result = DummyOrderingSchema.validate_order_by_field(order_by_value)
    assert validation_result == order_by_value


def test_validate_order_by_field__should_pass_when_value_in_allowed_fields_and_desc():
    test_field = "test_field"

    class DummyOrderingSchema(OrderingSchema):
        class Meta(OrderingSchema.Meta):
            allowed_fields = [test_field]

    order_by_value = [f"-{test_field}"]
    validation_result = DummyOrderingSchema.validate_order_by_field(order_by_value)
    assert validation_result == order_by_value


def test_validate_order_by_field__should_raise_validation_error_when_value_asc_not_in_allowed_fields():
    test_field = "allowed_field"

    class DummyOrderingSchema(OrderingSchema):
        class Meta(OrderingSchema.Meta):
            allowed_fields = [test_field]

    order_by_value = ["not_allowed_field"]
    with pytest.raises(ValueError):
        DummyOrderingSchema.validate_order_by_field(order_by_value)


def test_validate_order_by_field__should_raise_validation_error_when_value_desc_not_in_allowed_fields():
    test_field = "allowed_field"

    class DummyOrderingSchema(OrderingSchema):
        class Meta(OrderingSchema.Meta):
            allowed_fields = [test_field]

    order_by_value = ["-not_allowed_field"]
    with pytest.raises(ValueError):
        DummyOrderingSchema.validate_order_by_field(order_by_value)


def test_parsed_order_by__should_return_mapped_fields_when_allowed_fields_is_dict():
    class DummyOrderingSchema(OrderingSchema):
        class Meta(OrderingSchema.Meta):
            allowed_fields = {
                "field1": "mapped_field1",
                "field2": "mapped_field2",
            }

    ordering_schema = DummyOrderingSchema(order_by=["field1", "-field2"])
    assert ordering_schema.parsed_order_by == ["mapped_field1", "-mapped_field2"]


def test_parsed_order_by__should_return_original_fields_when_allowed_fields_is_not_dict():
    class DummyOrderingSchema(OrderingSchema):
        class Meta(OrderingSchema.Meta):
            allowed_fields = ["field1", "field2"]

    ordering_schema = DummyOrderingSchema(order_by=["field1", "-field2"])
    assert ordering_schema.parsed_order_by == ["field1", "-field2"]


def test_sort__should_return_queryset_when_no_order_by():
    ordering_schema = OrderingSchema(order_by=[])
    queryset = FakeQS()
    sorted_queryset = ordering_schema.sort(queryset)
    assert sorted_queryset is queryset


def test_sort__should_call_order_by_on_queryset_with_expected_args():
    order_by_value = ["test_field_1", "-test_field_2"]
    ordering_schema = OrderingSchema(order_by=order_by_value)

    queryset = FakeQS()
    queryset = ordering_schema.sort(queryset)
    assert queryset.is_ordered
    assert queryset.order_by_args == tuple(order_by_value)


def test_sort__should_raise_not_implemented_error():
    class DummyOrderingSchema(OrderingBaseSchema):
        pass

    with pytest.raises(NotImplementedError):
        DummyOrderingSchema().sort(FakeQS())


def test_sort__should_use_parsed_order_by():
    class DummyOrderingSchema(OrderingSchema):
        class Meta(OrderingSchema.Meta):
            allowed_fields = {
                "field1": "mapped_field1",
                "field2": "mapped_field2",
            }

    order_by_value = ["field1", "-field2"]
    ordering_schema = DummyOrderingSchema(order_by=order_by_value)

    queryset = FakeQS()
    queryset = ordering_schema.sort(queryset)
    assert queryset.is_ordered
    assert queryset.order_by_args == ("mapped_field1", "-mapped_field2")


def test_ordering_query_param__should_parse_custom_query_param():
    api = NinjaAPI(urls_namespace="test_ordering_query_param")

    class CustomOrderingSchema(OrderingSchema):
        class Meta(OrderingSchema.Meta):
            ordering_query_param = "ordering"

    @api.get("/items")
    def list_items(request, ordering: CustomOrderingSchema = Query(...)):
        return ordering.order_by

    client = TestClient(api)
    response = client.get("/items?ordering=name&ordering=-created_at")

    assert response.status_code == 200
    assert response.json() == ["name", "-created_at"]


def test_ordering_query_param__should_use_custom_name_in_openapi():
    api = NinjaAPI(urls_namespace="test_ordering_query_param_openapi")

    class CustomOrderingSchema(OrderingSchema):
        class Meta(OrderingSchema.Meta):
            ordering_query_param = "ordering"

    @api.get("/items")
    def list_items(request, ordering: CustomOrderingSchema = Query(...)):
        return ordering.order_by

    parameters = api.get_openapi_schema(path_prefix="")["paths"]["/items"]["get"][
        "parameters"
    ]
    parameter_names = {parameter["name"] for parameter in parameters}

    assert "ordering" in parameter_names
    assert "order_by" not in parameter_names
