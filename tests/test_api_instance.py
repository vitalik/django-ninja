from collections import Counter

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
    for _path, rtr in api._routers:
        for path_ops in rtr.path_operations.values():
            for op in path_ops.operations:
                assert op.api is api


def test_add_router_is_idempotent():
    test_api = NinjaAPI()
    test_router = Router()
    test_api.add_router("/", test_router)

    # Verify we handle reattempted registration properly
    match = r"Router has already been attached to API NinjaAPI:1.0.0 under '/'"
    with pytest.raises(ConfigError, match=match):
        test_api.add_router("/another-path", test_router)

    # Idempotent registration
    test_api.add_router("/", test_router)
    assert Counter(test_api._routers).get(("/", test_router), 0) == 1


def test_errors_reusing_router_under_different_prefix():
    test_api = NinjaAPI()
    test_router = Router()
    test_api.add_router("/", test_router)

    match = r"Router has already been attached to API NinjaAPI:1.0.0 under '/'"
    with pytest.raises(ConfigError, match=match):
        test_api.add_router("/other", test_router)


def test_errors_reusing_router_as_nested_router():
    root_level = NinjaAPI()
    reused = Router()
    root_level.add_router("/root", reused)
    level_1 = Router()
    root_level.add_router("/level_1", level_1)

    match = r"Router has already been attached to API NinjaAPI:1.0.0 under '/root'"
    with pytest.raises(ConfigError, match=match):
        level_1.add_router("/level_2", reused)


def test_errors_reusing_router_on_parent_router():
    root_level = NinjaAPI()
    parent = Router()
    root_level.add_router("/parent", parent)
    child = Router()
    parent.add_router("/child", child)

    match = (
        r"Router has already been attached to API NinjaAPI:1.0.0 under 'parent/child'"
    )
    with pytest.raises(ConfigError, match=match):
        parent.add_router("/sibling", child)


def test_errors_reusing_router_as_nested_router_with_same_registration_prefix():
    root_level = NinjaAPI()
    reused = Router()
    root_level.add_router("/root", reused)
    level_1 = Router()
    root_level.add_router("/level_1", level_1)

    match = r"Router has already been attached to API NinjaAPI:1.0.0 under '/root'"
    with pytest.raises(ConfigError, match=match):
        level_1.add_router("/root", reused)


@pytest.mark.parametrize(
    ("first_prefix", "second_prefix"),
    [
        pytest.param("/", "/", id="with_same_prefix"),
        pytest.param("/", "/different", id="with_different_prefix"),
    ],
)
def test_errors_reusing_router_in_other_api(first_prefix: str, second_prefix: str):
    first_api = NinjaAPI(title="FirstAPI", version="1.0.0")
    second_api = NinjaAPI(title="SecondAPI", version="1.0.0")
    router = Router()
    first_api.add_router(first_prefix, router)
    match = rf"Router has already been attached to API FirstAPI:1.0.0 under '{first_prefix}'"
    with pytest.raises(ConfigError, match=match):
        second_api.add_router(second_prefix, router)
