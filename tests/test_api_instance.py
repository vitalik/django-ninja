import pytest

from ninja import NinjaAPI, Router
from ninja.errors import ConfigError


def test_api_instance():
    """Test that operations are properly bound to API via bound routers."""
    api = NinjaAPI(urls_namespace="api-instance-test")
    router = Router()

    @api.get("/global")
    def global_op(request):
        pass

    @router.get("/router")
    def router_op(request):
        pass

    api.add_router("/", router)

    # Access URLs to trigger binding
    _ = api.urls

    # Check via bound routers (the new architecture)
    bound_routers = api._get_bound_routers()
    assert len(bound_routers) == 2  # default + extra

    for bound_router in bound_routers:
        for path_ops in bound_router.path_operations.values():
            for op in path_ops.operations:
                assert op.api is api


def test_reuse_router_requires_url_name_prefix():
    """Mounting same router twice requires url_name_prefix."""
    test_api = NinjaAPI(urls_namespace="reuse-test")
    test_router = Router()

    @test_router.get("/test")
    def test_op(request):
        pass

    test_api.add_router("/", test_router)

    # Same router mounted again without url_name_prefix should raise
    match = "Router is already mounted"
    with pytest.raises(ConfigError, match=match):
        test_api.add_router("/another-path", test_router)


def test_reuse_router_with_url_name_prefix():
    """Same router can be mounted multiple times with different url_name_prefix."""
    test_api = NinjaAPI(urls_namespace="reuse-prefix-test")
    test_router = Router()

    @test_router.get("/test")
    def test_op(request):
        pass

    test_api.add_router("/v1", test_router, url_name_prefix="v1")
    test_api.add_router("/v2", test_router, url_name_prefix="v2")

    # Should work - verify URLs are generated
    _ = test_api.urls

    # Both mounts should work
    bound_routers = test_api._get_bound_routers()
    # default router + 2 mounts of test_router
    assert len(bound_routers) == 3
