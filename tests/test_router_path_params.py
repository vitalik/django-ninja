import pytest

from ninja import NinjaAPI, Path, Router
from ninja.testing import TestClient

api = NinjaAPI()
router_with_path_type = Router()
router_without_path_type = Router()
router_with_multiple = Router()


@router_with_path_type.get("/metadata")
def get_item_metadata(request, item_id: int = Path(None)) -> int:
    return item_id


@router_without_path_type.get("/")
def get_item_metadata_2(request, item_id: str = Path(None)) -> str:
    return item_id


@router_without_path_type.get("/metadata")
def get_item_metadata_3(request, item_id: str = Path(None)) -> str:
    return item_id


@router_without_path_type.get("/")
def get_item_metadata_4(request, item_id: str = Path(None)) -> str:
    return item_id


@router_with_multiple.get("/metadata/{kind}")
def get_item_metadata_5(
    request, item_id: int = Path(None), name: str = Path(None), kind: str = Path(None)
) -> str:
    return f"{item_id} {name} {kind}"


api.add_router("/with_type/{int:item_id}", router_with_path_type)
api.add_router("/without_type/{item_id}", router_without_path_type)
api.add_router("/with_multiple/{int:item_id}/name/{name}", router_with_multiple)

client = TestClient(api)


@pytest.mark.parametrize(
    "path,expected_status,expected_response",
    [
        ("/with_type/1/metadata", 200, 1),
        ("/without_type/1/metadata", 200, "1"),
        ("/without_type/abc/metadata", 200, "abc"),
        ("/with_multiple/99/name/foo/metadata/timestamp", 200, "99 foo timestamp"),
    ],
)
def test_router_with_path_params(path, expected_status, expected_response):
    response = client.get(path)
    assert response.status_code == expected_status
    assert response.json() == expected_response


@pytest.mark.parametrize(
    "path,expected_exception,expect_exception_contains",
    [
        ("/with_type/abc/metadata", Exception, "Cannot resolve"),
        ("/with_type//metadata", Exception, "Cannot resolve"),
        ("/with_type/null/metadata", Exception, "Cannot resolve"),
        ("/with_type", Exception, "Cannot resolve"),
        ("/with_type/", Exception, "Cannot resolve"),
        ("/with_type//", Exception, "Cannot resolve"),
        ("/with_type/null", Exception, "Cannot resolve"),
        ("/with_type/null/", Exception, "Cannot resolve"),
        ("/without_type", Exception, "Cannot resolve"),
        ("/without_type/", Exception, "Cannot resolve"),
        ("/without_type//", Exception, "Cannot resolve"),
        ("/with_multiple/abc/name/foo/metadata/timestamp", Exception, "Cannot resolve"),
        ("/with_multiple/99", Exception, "Cannot resolve"),
    ],
)
def test_router_with_path_params_nomatch(
    path, expected_exception, expect_exception_contains
):
    with pytest.raises(expected_exception, match=expect_exception_contains):
        client.get(path)
