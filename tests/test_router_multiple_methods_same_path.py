from ninja import NinjaAPI, Router
from ninja.testing import TestClient


def test_multiple_routers_same_path_different_methods():
    api = NinjaAPI()

    router1 = Router()

    @router1.get("/items")
    def get_items(request):
        return {"method": "GET", "router": 1}

    @router1.post("/items")
    def create_item(request):
        return {"method": "POST", "router": 1}

    router2 = Router()

    @router2.put("/items")
    def update_item(request):
        return {"method": "PUT", "router": 2}

    @router2.delete("/items")
    def delete_item(request):
        return {"method": "DELETE", "router": 2}

    api.add_router("", router1)
    api.add_router("", router2)

    client = TestClient(api)

    response = client.get("/items")
    assert response.status_code == 200
    assert response.json() == {"method": "GET", "router": 1}

    response = client.post("/items")
    assert response.status_code == 200
    assert response.json() == {"method": "POST", "router": 1}

    response = client.put("/items")
    assert response.status_code == 200
    assert response.json() == {"method": "PUT", "router": 2}

    response = client.delete("/items")
    assert response.status_code == 200
    assert response.json() == {"method": "DELETE", "router": 2}

    # unsupported method returns 405
    response = client.patch("/items")
    assert response.status_code == 405


def test_api_and_router_same_path_different_methods():
    api = NinjaAPI()

    @api.get("/users")
    def get_users(request):
        return {"method": "GET", "source": "api"}

    router = Router()

    @router.put("/users")
    def update_user(request):
        return {"method": "PUT", "source": "router"}

    @router.delete("/users")
    def delete_user(request):
        return {"method": "DELETE", "source": "router"}

    api.add_router("", router)

    client = TestClient(api)

    response = client.get("/users")
    assert response.status_code == 200
    assert response.json() == {"method": "GET", "source": "api"}

    response = client.put("/users")
    assert response.status_code == 200
    assert response.json() == {"method": "PUT", "source": "router"}

    response = client.delete("/users")
    assert response.status_code == 200
    assert response.json() == {"method": "DELETE", "source": "router"}

    # unsupported method returns 405
    response = client.post("/users")
    assert response.status_code == 405


def test_overlapping_methods_different_routers():
    api = NinjaAPI()

    router1 = Router()

    @router1.get("/overlap")
    def get_overlap_1(request):
        return {"source": "router1"}

    router2 = Router()

    @router2.get("/overlap")
    def get_overlap_2(request):
        return {"source": "router2"}

    api.add_router("", router1)
    api.add_router("", router2)

    client = TestClient(api)

    # first router's handler should be used
    response = client.get("/overlap")
    assert response.status_code == 200
