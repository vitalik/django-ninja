from ninja import NinjaAPI, Router


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
        for path_ops in rtr.operations.values():
            for op in path_ops.operations:
                assert op.api is api
