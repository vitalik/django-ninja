import pytest
from ninja import Router, Cookie, Header
from client import NinjaClient

router = Router()


@router.get("/headers1")
def headers1(request, user_agent: str = Header(...)):
    return user_agent


@router.get("/headers2")
def headers2(request, ua: str = Header(..., alias="User-Agent")):
    return ua


@router.get("/headers3")
def headers3(request, content_length: int = Header(...)):
    return content_length


@router.get("/headers4")
def headers4(request, c_len: int = Header(..., alias="Content-length")):
    return c_len


@router.get("/cookies1")
def cookies1(request, weapon: str = Cookie(...)):
    return weapon


@router.get("/cookies2")
def cookies2(request, wpn: str = Cookie(..., alias="weapon")):
    return wpn


client = NinjaClient(router)


@pytest.mark.parametrize(
    "path,expected_status,expected_response",
    [
        ("/headers1", 200, "Ninja"),
        ("/headers2", 200, "Ninja"),
        ("/headers3", 200, 10),
        ("/headers4", 200, 10),
        ("/cookies1", 200, "shuriken"),
        ("/cookies2", 200, "shuriken"),
    ],
)
def test_headers(path, expected_status, expected_response):
    response = client.get(
        path,
        headers={"User-Agent": "Ninja", "Content-Length": "10"},
        COOKIES={"weapon": "shuriken"},
    )
    assert response.status_code == expected_status, response.content
    assert response.json() == expected_response
