import pytest
from django.db.models import QuerySet

from ninja import OrderingSchema


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
        class Config(OrderingSchema.Config):
            allowed_fields = [test_field]

    order_by_value = [test_field]
    validation_result = DummyOrderingSchema.validate_order_by_field(order_by_value)
    assert validation_result == order_by_value


def test_validate_order_by_field__should_pass_when_value_in_allowed_fields_and_desc():
    test_field = "test_field"

    class DummyOrderingSchema(OrderingSchema):
        class Config(OrderingSchema.Config):
            allowed_fields = [test_field]

    order_by_value = [f"-{test_field}"]
    validation_result = DummyOrderingSchema.validate_order_by_field(order_by_value)
    assert validation_result == order_by_value


def test_validate_order_by_field__should_raise_validation_error_when_value_asc_not_in_allowed_fields():
    test_field = "allowed_field"

    class DummyOrderingSchema(OrderingSchema):
        class Config(OrderingSchema.Config):
            allowed_fields = [test_field]

    order_by_value = ["not_allowed_field"]
    with pytest.raises(ValueError):
        DummyOrderingSchema.validate_order_by_field(order_by_value)


def test_validate_order_by_field__should_raise_validation_error_when_value_desc_not_in_allowed_fields():
    test_field = "allowed_field"

    class DummyOrderingSchema(OrderingSchema):
        class Config(OrderingSchema.Config):
            allowed_fields = [test_field]

    order_by_value = ["-not_allowed_field"]
    with pytest.raises(ValueError):
        DummyOrderingSchema.validate_order_by_field(order_by_value)


def test_sort__should_call_order_by_on_queryset_with_expected_args():
    order_by_value = ["test_field_1", "-test_field_2"]
    ordering_schema = OrderingSchema(order_by=order_by_value)

    queryset = FakeQS()
    queryset = ordering_schema.sort(queryset)
    assert queryset.is_ordered
    assert queryset.order_by_args == tuple(order_by_value)
