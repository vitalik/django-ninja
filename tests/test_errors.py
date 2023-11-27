import pickle

from ninja.errors import HttpError, ValidationError


def test_validation_error_is_picklable_and_unpicklable():
    error_to_serialize = ValidationError([{"testkey": "testvalue"}])

    serialized = pickle.dumps(error_to_serialize)
    assert serialized  # Not empty

    deserialized = pickle.loads(serialized)
    assert isinstance(deserialized, ValidationError)
    assert deserialized.errors == error_to_serialize.errors


def test_http_error_is_picklable_and_unpicklable():
    error_to_serialize = HttpError(500, "Test error")

    serialized = pickle.dumps(error_to_serialize)
    assert serialized  # Not empty

    deserialized = pickle.loads(serialized)
    assert isinstance(deserialized, HttpError)
    assert deserialized.status_code == error_to_serialize.status_code
    assert deserialized.message == error_to_serialize.message
