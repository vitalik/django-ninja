import uuid
from unittest.mock import Mock

import pytest

from ninja.errors import ConfigError
from ninja.signature.utils import NinjaUUIDConverter, inject_contribute_args


def test_uuid_converter():
    conv = NinjaUUIDConverter()
    assert isinstance(conv.to_url(uuid.uuid4()), str)


def test_inject_contribute_args():
    def test_func():
        pass

    test_schema = Mock()
    test_source = Mock()
    inject_contribute_args(test_func, "test", test_schema, test_source)
    assert hasattr(test_func, "_ninja_contribute_args")
    assert test_func._ninja_contribute_args[0] == ("test", test_schema, test_source)


def test_inject_contribute_args_with_existing_args():
    def test_func():
        pass

    test_schema = Mock()
    test_source = Mock()
    inject_contribute_args(test_func, "test", test_schema, test_source)

    test_schema2 = Mock()
    test_source2 = Mock()
    inject_contribute_args(test_func, "test2", test_schema2, test_source2)

    assert hasattr(test_func, "_ninja_contribute_args")
    assert test_func._ninja_contribute_args[0] == ("test", test_schema, test_source)
    assert test_func._ninja_contribute_args[1] == ("test2", test_schema2, test_source2)
