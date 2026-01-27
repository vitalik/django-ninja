from typing import Annotated
from ninja import Header


CustomHeader = Annotated[str, Header(alias="X-Custom-Header")]


@api.get("/events")
def events(request, custom_header: CustomHeader):
    return {"received": custom_header}
