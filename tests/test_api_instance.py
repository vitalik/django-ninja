from unittest import mock

import pytest

from ninja import NinjaAPI, Router
from ninja.errors import ConfigError

api = NinjaAPI()
router = Router()


@api.get("/global")
def global_op(request):
    pass


@router.get("/router")
def router_op(request):
    pass


api.add_router("/", router)


def test_api_instance():
    assert len(api._routers) == 2  # default + extra
    for path, rtr in api._routers:
        for path_ops in rtr.path_operations.values():
            for op in path_ops.operations:
                assert op.api is api


def test_reuse_router_error():
    test_api = NinjaAPI()
    test_router = Router()
    test_api.add_router("/", test_router)

    # django debug server can attempt to import the urls twice when errors exist
    # verify we get the correct error reported
    match = "Router@'/another-path' has already been attached to API NinjaAPI:1.0.0"
    with pytest.raises(ConfigError, match=match):
        with mock.patch("ninja.main._imported_while_running_in_debug_server", False):
            test_api.add_router("/another-path", test_router)

    # The error should be ignored under debug server to allow other errors to be reported
    with mock.patch("ninja.main._imported_while_running_in_debug_server", True):
        test_api.add_router("/another-path", test_router)
