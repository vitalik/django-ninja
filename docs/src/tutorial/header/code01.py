from ninja import Header


@api.get("/events")
def events(request, custom_header: str = Header(alias="X-Custom-Header")):
    return {"received": custom_header}
