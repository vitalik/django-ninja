from ninja import Header


@api.get("/events")
def events(request, user_agent: str | None = Header(None)):
    return {"user_agent": user_agent}


# Using alias instead of argument name
@api.get("/events")
def events(request, ua: str | None = Header(None, alias="User-Agent")):
    return {"user_agent": ua}


# Python 3.9+ Annotated
from typing import Annotated


UserAgent = Annotated[str | None, Header(None)]


@api.get("/events")
def events(request, user_agent: UserAgent):
    return {"user_agent": user_agent}
