import pytest
from django.test import Client
from someapp.models import Category


@pytest.fixture
def categories():
    yield [Category.objects.create(title=title) for title in ["C", "E", "B", "D", "A"]]
    Category.objects.all().delete()


@pytest.fixture
def duplicate_categories():
    yield [Category.objects.create(title=title) for title in ["A", "B", "B", "B", "C"]]
    Category.objects.all().delete()


@pytest.mark.django_db
def test_cursor_pagination_single_page(client: Client, categories):
    response = client.get("/api/events/categories")
    assert response.status_code == 200, response.json()
    assert response.json() == {
        "results": [
            {"title": "A"},
            {"title": "B"},
            {"title": "C"},
            {"title": "D"},
            {"title": "E"},
        ],
        "count": 5,
        "next": None,
        "previous": None,
    }


@pytest.mark.django_db
def test_cursor_pagination_iteration(client: Client, categories):
    response = client.get("/api/events/categories", data={"limit": 2})
    assert response.status_code == 200, response.json()
    assert response.json()["results"] == [{"title": "A"}, {"title": "B"}]
    next_url = response.json()["next"]
    assert next_url is not None
    assert response.json()["previous"] is None
    assert response.json()["count"] == 5

    # follow next page link
    response = client.get(next_url)
    assert response.status_code == 200, response.json()
    assert response.json()["results"] == [{"title": "C"}, {"title": "D"}]
    previous_url = response.json()["previous"]
    assert previous_url is not None
    assert response.json()["count"] == 5

    # follow previous page link
    response = client.get(previous_url)
    assert response.status_code == 200, response.json()
    assert response.json()["results"] == [{"title": "A"}, {"title": "B"}]


def test_invalid_cursor(client: Client):
    response = client.get("/api/events/categories", data={"cursor": "invalid"})
    assert response.status_code == 422
    assert "Invalid cursor." in response.json()["detail"][0]["msg"]


@pytest.mark.django_db
def test_cursor_pagination_duplicates(client: Client, duplicate_categories):
    # test cursors that require offets for duplicate values
    response = client.get("/api/events/categories", data={"limit": 2})
    assert response.status_code == 200, response.json()
    assert response.json()["results"] == [{"title": "A"}, {"title": "B"}]

    response = client.get(response.json()["next"])
    assert response.status_code == 200, response.json()
    assert response.json()["results"] == [{"title": "B"}, {"title": "B"}]

    response = client.get(response.json()["next"])
    assert response.status_code == 200, response.json()
    assert response.json()["results"] == [{"title": "C"}]
    assert response.json()["next"] is None

    response = client.get(response.json()["previous"])
    assert response.status_code == 200, response.json()
    assert response.json()["results"] == [{"title": "B"}, {"title": "B"}]
    assert response.json()["next"] is not None
