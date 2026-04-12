import pytest
import pytest_asyncio
from someapp.models import Category, Event

from ninja import NinjaAPI, Router
from ninja.testing import TestAsyncClient, TestClient  # noqa: E402

# Routes are now prefixed with the lowercase model name, so with the router
# mounted at the API root ("") the paths become /api/category/ and
# /api/category/{id}.  Fixtures mount at "" to avoid a double prefix.


@pytest.fixture
def client():
    api = NinjaAPI()
    router = Router()
    router.add_model_api(Category)
    api.add_router("", router)
    return TestClient(api)


@pytest.mark.django_db
def test_list_empty(client):
    response = client.get("/category/")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.django_db
def test_create(client):
    response = client.post("/category/", json={"title": "Python"})
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Python"
    assert "id" in data


@pytest.mark.django_db
def test_list_after_create(client):
    client.post("/category/", json={"title": "Django"})
    response = client.get("/category/")
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 1
    assert items[0]["title"] == "Django"


@pytest.mark.django_db
def test_retrieve(client):
    create_resp = client.post("/category/", json={"title": "Ninja"})
    pk = create_resp.json()["id"]

    response = client.get(f"/category/{pk}")
    assert response.status_code == 200
    assert response.json()["title"] == "Ninja"


@pytest.mark.django_db
def test_retrieve_not_found(client):
    response = client.get("/category/9999")
    assert response.status_code == 404


@pytest.mark.django_db
def test_update_put(client):
    create_resp = client.post("/category/", json={"title": "Old"})
    pk = create_resp.json()["id"]

    response = client.put(f"/category/{pk}", json={"title": "New"})
    assert response.status_code == 200
    assert response.json()["title"] == "New"


@pytest.mark.django_db
def test_partial_update_patch(client):
    create_resp = client.post("/category/", json={"title": "Original"})
    pk = create_resp.json()["id"]

    response = client.patch(f"/category/{pk}", json={"title": "Patched"})
    assert response.status_code == 200
    assert response.json()["title"] == "Patched"


@pytest.mark.django_db
def test_delete(client):
    create_resp = client.post("/category/", json={"title": "ToDelete"})
    pk = create_resp.json()["id"]

    response = client.delete(f"/category/{pk}")
    assert response.status_code == 204

    assert client.get(f"/category/{pk}").status_code == 404


@pytest.mark.django_db
def test_operations_subset():
    """Only the requested operations are registered."""
    api = NinjaAPI()
    router = Router()
    router.add_model_api(Category, operations=["list", "retrieve"])
    api.add_router("", router)
    c = TestClient(api)

    assert c.get("/category/").status_code == 200
    assert c.post("/category/", json={"title": "x"}).status_code == 405
    assert c.delete("/category/1").status_code == 405


@pytest.mark.django_db
def test_exclude_fields():
    """Excluded fields must not appear in the response schema."""
    api = NinjaAPI()
    router = Router()
    router.add_model_api(Event, exclude=["category"])
    api.add_router("", router)
    c = TestClient(api)

    resp = c.post(
        "/event/",
        json={
            "title": "PyCon",
            "start_date": "2024-01-01",
            "end_date": "2024-01-03",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "title" in data
    assert "category" not in data


# ===========================================================================
# OpenAPI / Swagger schema tests
# ===========================================================================


@pytest.fixture(scope="module")
def category_schema():
    """OpenAPI schema for a basic add_model_api(Category) setup."""
    api = NinjaAPI()
    router = Router()
    router.add_model_api(Category)
    api.add_router("", router)
    return api.get_openapi_schema()


def test_schema_paths_exist(category_schema):
    """Both collection and detail paths must be present."""
    paths = category_schema["paths"]
    assert "/api/category/" in paths
    assert "/api/category/{id}" in paths


def test_schema_collection_methods(category_schema):
    """Collection path must expose GET and POST only."""
    collection = category_schema["paths"]["/api/category/"]
    assert set(collection.keys()) == {"get", "post"}


def test_schema_detail_methods(category_schema):
    """Detail path must expose GET, PUT, PATCH and DELETE only."""
    detail = category_schema["paths"]["/api/category/{id}"]
    assert set(detail.keys()) == {"get", "put", "patch", "delete"}


def test_schema_list_response(category_schema):
    """GET / must return a 200 array of CategorySchema."""
    get_op = category_schema["paths"]["/api/category/"]["get"]
    assert 200 in get_op["responses"]
    content = get_op["responses"][200]["content"]["application/json"]["schema"]
    assert content["type"] == "array"
    assert content["items"]["$ref"] == "#/components/schemas/CategorySchema"


def test_schema_create_response_201(category_schema):
    """POST / must return 201 with CategorySchema body."""
    post_op = category_schema["paths"]["/api/category/"]["post"]
    assert 201 in post_op["responses"]
    ref = post_op["responses"][201]["content"]["application/json"]["schema"]["$ref"]
    assert ref == "#/components/schemas/CategorySchema"


def test_schema_create_request_body(category_schema):
    """POST / request body must reference CategoryCreateSchema."""
    post_op = category_schema["paths"]["/api/category/"]["post"]
    ref = post_op["requestBody"]["content"]["application/json"]["schema"]["$ref"]
    assert ref == "#/components/schemas/CategoryCreateSchema"
    assert post_op["requestBody"]["required"] is True


def test_schema_retrieve_response(category_schema):
    """GET /{id} must return 200 with CategorySchema."""
    get_op = category_schema["paths"]["/api/category/{id}"]["get"]
    assert 200 in get_op["responses"]
    ref = get_op["responses"][200]["content"]["application/json"]["schema"]["$ref"]
    assert ref == "#/components/schemas/CategorySchema"


def test_schema_retrieve_path_param(category_schema):
    """GET /{id} must declare an integer path parameter named 'id'."""
    params = category_schema["paths"]["/api/category/{id}"]["get"]["parameters"]
    id_param = next(p for p in params if p["name"] == "id")
    assert id_param["in"] == "path"
    assert id_param["required"] is True
    assert id_param["schema"]["type"] == "integer"


def test_schema_update_request_body(category_schema):
    """PUT /{id} must use CategoryCreateSchema (all required fields)."""
    put_op = category_schema["paths"]["/api/category/{id}"]["put"]
    ref = put_op["requestBody"]["content"]["application/json"]["schema"]["$ref"]
    assert ref == "#/components/schemas/CategoryCreateSchema"


def test_schema_partial_update_request_body(category_schema):
    """PATCH /{id} must use CategoryPatchSchema (all optional fields)."""
    patch_op = category_schema["paths"]["/api/category/{id}"]["patch"]
    ref = patch_op["requestBody"]["content"]["application/json"]["schema"]["$ref"]
    assert ref == "#/components/schemas/CategoryPatchSchema"


def test_schema_summaries(category_schema):
    """All generated operations must carry the correct human-readable summary."""
    paths = category_schema["paths"]
    assert paths["/api/category/"]["get"]["summary"] == "List Category"
    assert paths["/api/category/"]["post"]["summary"] == "Create Category"
    assert paths["/api/category/{id}"]["get"]["summary"] == "Retrieve Category"
    assert paths["/api/category/{id}"]["put"]["summary"] == "Update Category"
    assert paths["/api/category/{id}"]["patch"]["summary"] == "Partial Update Category"
    assert paths["/api/category/{id}"]["delete"]["summary"] == "Delete Category"


def test_schema_default_tags(category_schema):
    """All operations default to the model class name as their tag."""
    paths = category_schema["paths"]
    for path_item in paths.values():
        for operation in path_item.values():
            assert operation["tags"] == ["Category"]


def test_schema_custom_tags():
    """tags= kwarg propagates to every generated operation."""
    api = NinjaAPI()
    router = Router()
    router.add_model_api(Category, tags=["products", "shop"])
    api.add_router("", router)
    schema = api.get_openapi_schema()

    for path_item in schema["paths"].values():
        for operation in path_item.values():
            assert operation["tags"] == ["products", "shop"]


def test_schema_response_schema_has_id(category_schema):
    """CategorySchema (response) must include the 'id' primary-key field."""
    props = category_schema["components"]["schemas"]["CategorySchema"]["properties"]
    assert "id" in props


def test_schema_create_schema_excludes_id(category_schema):
    """CategoryCreateSchema must NOT include the auto PK 'id'."""
    props = category_schema["components"]["schemas"]["CategoryCreateSchema"][
        "properties"
    ]
    assert "id" not in props
    assert "title" in props
    required = category_schema["components"]["schemas"]["CategoryCreateSchema"].get(
        "required", []
    )
    assert "title" in required


def test_schema_patch_schema_all_optional(category_schema):
    """CategoryPatchSchema must have no required fields (all fields optional)."""
    patch_schema = category_schema["components"]["schemas"]["CategoryPatchSchema"]
    assert "required" not in patch_schema or patch_schema.get("required") == []


def test_schema_operations_subset():
    """When operations= is given, only those paths/methods appear in the schema."""
    api = NinjaAPI()
    router = Router()
    router.add_model_api(Category, operations=["list", "retrieve"])
    api.add_router("", router)
    schema = api.get_openapi_schema()

    paths = schema["paths"]
    assert "/api/category/" in paths
    assert set(paths["/api/category/"].keys()) == {"get"}  # no POST

    assert "/api/category/{id}" in paths
    assert set(paths["/api/category/{id}"].keys()) == {"get"}  # no PUT/PATCH/DELETE


def test_schema_exclude_field_removed_from_all_component_schemas():
    """Fields listed in exclude= must be absent from all three component schemas."""
    api = NinjaAPI()
    router = Router()
    router.add_model_api(Event, exclude=["category"])
    api.add_router("", router)
    schema = api.get_openapi_schema()

    components = schema["components"]["schemas"]
    for schema_name in ("EventSchema", "EventCreateSchema", "EventPatchSchema"):
        assert schema_name in components, f"Missing schema: {schema_name}"
        props = components[schema_name]["properties"]
        assert (
            "category" not in props
        ), f"'category' should be excluded from {schema_name}"


# ===========================================================================
# Async CRUD tests  (add_async_model_api)
# ===========================================================================


@pytest_asyncio.fixture
async def async_client():
    api = NinjaAPI()
    router = Router()
    router.add_async_model_api(Category)
    api.add_router("", router)
    return TestAsyncClient(api)


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_async_list_empty(async_client):
    response = await async_client.get("/category/")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_async_create(async_client):
    response = await async_client.post("/category/", json={"title": "Async"})
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Async"
    assert "id" in data


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_async_list_after_create(async_client):
    await async_client.post("/category/", json={"title": "Django"})
    response = await async_client.get("/category/")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["title"] == "Django"


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_async_retrieve(async_client):
    create_resp = await async_client.post("/category/", json={"title": "Ninja"})
    pk = create_resp.json()["id"]

    response = await async_client.get(f"/category/{pk}")
    assert response.status_code == 200
    assert response.json()["title"] == "Ninja"


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_async_retrieve_not_found(async_client):
    response = await async_client.get("/category/9999")
    assert response.status_code == 404


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_async_update_put(async_client):
    create_resp = await async_client.post("/category/", json={"title": "Old"})
    pk = create_resp.json()["id"]

    response = await async_client.put(f"/category/{pk}", json={"title": "New"})
    assert response.status_code == 200
    assert response.json()["title"] == "New"


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_async_partial_update_patch(async_client):
    create_resp = await async_client.post("/category/", json={"title": "Original"})
    pk = create_resp.json()["id"]

    response = await async_client.patch(f"/category/{pk}", json={"title": "Patched"})
    assert response.status_code == 200
    assert response.json()["title"] == "Patched"


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_async_delete(async_client):
    create_resp = await async_client.post("/category/", json={"title": "ToDelete"})
    pk = create_resp.json()["id"]

    response = await async_client.delete(f"/category/{pk}")
    assert response.status_code == 204

    assert (await async_client.get(f"/category/{pk}")).status_code == 404


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_async_operations_subset():
    """Only requested operations are wired up."""
    api = NinjaAPI()
    router = Router()
    router.add_async_model_api(Category, operations=["list", "retrieve"])
    api.add_router("", router)
    c = TestAsyncClient(api)

    assert (await c.get("/category/")).status_code == 200
    assert (await c.post("/category/", json={"title": "x"})).status_code == 405
    assert (await c.delete("/category/1")).status_code == 405


# --- OpenAPI schema for async endpoints ---


@pytest.fixture(scope="module")
def async_category_schema():
    api = NinjaAPI()
    router = Router()
    router.add_async_model_api(Category)
    api.add_router("", router)
    return api.get_openapi_schema()


def test_async_schema_paths_exist(async_category_schema):
    paths = async_category_schema["paths"]
    assert "/api/category/" in paths
    assert "/api/category/{id}" in paths


def test_async_schema_collection_methods(async_category_schema):
    assert set(async_category_schema["paths"]["/api/category/"].keys()) == {
        "get",
        "post",
    }


def test_async_schema_detail_methods(async_category_schema):
    assert set(async_category_schema["paths"]["/api/category/{id}"].keys()) == {
        "get",
        "put",
        "patch",
        "delete",
    }


def test_async_schema_create_response_201(async_category_schema):
    post_op = async_category_schema["paths"]["/api/category/"]["post"]
    assert 201 in post_op["responses"]


def test_async_schema_matches_sync_schema():
    """The OpenAPI output of add_async_model_api must be identical to add_model_api."""
    sync_api = NinjaAPI()
    sync_router = Router()
    sync_router.add_model_api(Category, tags=["CmpTest"])
    sync_api.add_router("", sync_router)

    async_api = NinjaAPI()
    async_router = Router()
    async_router.add_async_model_api(Category, tags=["CmpTest"])
    async_api.add_router("", async_router)

    assert (
        sync_api.get_openapi_schema()["paths"]
        == async_api.get_openapi_schema()["paths"]
    )
    assert (
        sync_api.get_openapi_schema()["components"]
        == async_api.get_openapi_schema()["components"]
    )
