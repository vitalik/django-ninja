from ninja import Router

router = Router()


@router.get("/endpoint/", url_name="registered-late")
def endpoint(request):
    return "response"
