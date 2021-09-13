import pytest

from ninja import Cookie, Header, Router
from ninja.testing import TestClient

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


@router.get("/headers5")
def headers5(request, missing: int = Header(...)):
    return missing


@router.get("/cookies1")
def cookies1(request, weapon: str = Cookie(...)):
    return weapon


@router.get("/cookies2")
def cookies2(request, wpn: str = Cookie(..., alias="weapon")):
    return wpn


client = TestClient(router)


@pytest.mark.parametrize(
    "path,expected_status,expected_response",
    [
        ("/headers1", 200, "Ninja"),
        ("/headers2", 200, "Ninja"),
        ("/headers3", 200, 10),
        ("/headers4", 200, 10),
        (
            "/headers5",
            422,
            {
                "detail": [
                    {
                        "loc": ["header", "missing"],
                        "msg": "field required",
                        "type": "value_error.missing",
                    }
                ]
            },
        ),
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
