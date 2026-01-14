from datetime import date, timedelta
from http import HTTPStatus
from typing import List

import pytest
from django.test import override_settings
from someapp.api import EventSchema  # pyright: ignore[reportMissingImports]
from someapp.models import Category, Event  # pyright: ignore[reportMissingImports]

from ninja import NinjaAPI
from ninja.pagination import CursorPagination, paginate
from ninja.testing import TestAsyncClient, TestClient

api = NinjaAPI()


@api.get("/cursor_events", response=List[EventSchema])
@paginate(CursorPagination, ordering=("start_date",), page_size=10)
def cursor_events(request, **kwargs):
    return Event.objects.all()


@api.get("/cursor_events_reverse", response=List[EventSchema])
@paginate(CursorPagination, ordering=("-start_date",), page_size=10)
def cursor_events_reverse(request, **kwargs):
    return Event.objects.all()


@api.get("/cursor_events_end_date_offset", response=List[EventSchema])
@paginate(CursorPagination, ordering=("end_date", "start_date"), page_size=2)
def cursor_events_end_date_offset(request, **kwargs):
    return Event.objects.all()


@api.get("/cursor_events_default_size", response=List[EventSchema])
@paginate(CursorPagination, ordering=("start_date",))
def cursor_events_default_size(request, **kwargs):
    return Event.objects.all()


@api.get("/cursor_events_with_params", response=List[EventSchema])
@paginate(CursorPagination, ordering=("start_date",), page_size=10)
def cursor_events_with_params(request, title_filter: str = "", **kwargs):
    # API method with a filter in query parameter
    if title_filter:
        return Event.objects.filter(title__icontains=title_filter)
    return Event.objects.all()


# Async versions of all endpoints
@api.get("/async_cursor_events", response=List[EventSchema])
@paginate(CursorPagination, ordering=("start_date",), page_size=10)
async def async_cursor_events(request, **kwargs):
    return Event.objects.all()


@api.get("/async_cursor_events_reverse", response=List[EventSchema])
@paginate(CursorPagination, ordering=("-start_date",), page_size=10)
async def async_cursor_events_reverse(request, **kwargs):
    return Event.objects.all()


@api.get("/async_cursor_events_end_date_offset", response=List[EventSchema])
@paginate(CursorPagination, ordering=("end_date", "start_date"), page_size=2)
async def async_cursor_events_end_date_offset(request, **kwargs):
    return Event.objects.all()


@api.get("/async_cursor_events_default_size", response=List[EventSchema])
@paginate(CursorPagination, ordering=("start_date",))
async def async_cursor_events_default_size(request, **kwargs):
    return Event.objects.all()


@api.get("/async_cursor_events_with_params", response=List[EventSchema])
@paginate(CursorPagination, ordering=("start_date",), page_size=10)
async def async_cursor_events_with_params(request, title_filter: str = "", **kwargs):
    # API method with a filter in query parameter
    if title_filter:
        return Event.objects.filter(title__icontains=title_filter)
    return Event.objects.all()


client = TestClient(api)
async_client = TestAsyncClient(api)


@pytest.fixture(autouse=True)
def clean_db(transactional_db):
    """Clean up categories and events before and after each test."""
    Category.objects.all().delete()
    Event.objects.all().delete()
    yield
    Category.objects.all().delete()
    Event.objects.all().delete()


@pytest.fixture()
def start_date():
    return date(2023, 1, 1)


@pytest.fixture(autouse=True)
def events(transactional_db, start_date):
    """Create a number of test events."""

    events = []
    for i in range(1, 11):
        event = Event(
            title=f"Event {i}",  # 1-10
            start_date=start_date + timedelta(days=i),  # sequential start dates
            end_date=start_date
            + timedelta(
                days=((i - 1) // 3) + 1
            ),  # end dates 1, 1, 1, 2, 2, 2, 3, 3, 3, 4
        )
        events.append(event)

    return Event.objects.bulk_create(events)


@pytest.fixture(autouse=True)
def special_events(transactional_db, start_date, events):
    """Create a number of special events occurring after the last ones"""
    n_events = len(events)
    special_events = []
    for i in range(n_events + 1, n_events + 4):
        event = Event(
            title=f"Special Event {i}",  # 11-13
            start_date=start_date + timedelta(days=i),  # sequential start dates
            end_date=start_date
            + timedelta(days=((i - 1) // 3) + 1),  # end dates 4, 4, 5
        )
        special_events.append(event)

    return Event.objects.bulk_create(special_events)


def test_cursor_pagination_first_page():
    """Test first page of cursor pagination."""

    response = client.get("/cursor_events?page_size=5").json()

    assert len(response["results"]) == 5
    assert response["results"][0]["title"] == "Event 1"
    assert response["results"][-1]["title"] == "Event 5"
    assert response["next"] is not None
    assert response["previous"] is None


def test_cursor_pagination_with_cursor():
    """Test navigation using cursor."""

    # Get first page to obtain next cursor
    first_response = client.get("/cursor_events").json()

    assert len(first_response["results"]) == 10
    assert first_response["next"] is not None

    if first_response["next"]:
        # we can't rely on `next` being a well-formed URL, because the testclient
        # httprequest mock does not pass the path, so we extract the cursor instead
        next_cursor = first_response["next"].split("cursor=")[1].split("&")[0]

        # Use cursor to get next page
        response = client.get(f"/cursor_events?cursor={next_cursor}").json()

        assert len(response["results"]) == 3  # Remaining 3 events
        assert response["next"] is None
        assert response["previous"] is not None


def test_cursor_pagination_reverse_ordering():
    """Test cursor pagination with reverse ordering."""

    response = client.get("/cursor_events_reverse").json()

    assert len(response["results"]) == 10
    # With reverse ordering, should start from the end
    assert response["results"][0]["title"] == "Special Event 13"
    assert response["next"] is not None
    assert response["previous"] is None


def test_cursor_pagination_end_date_offset():
    """Test cursor pagination handles duplicate end_date values"""

    response = client.get("/cursor_events_end_date_offset").json()

    # Should handle events with same end_date by using id as secondary ordering
    assert len(response["results"]) == 2

    # Verify ordering is consistent across pages
    all_results = []
    current_response = response

    while True:
        all_results.extend(current_response["results"])
        if not current_response["next"]:
            break
        next_cursor = current_response["next"].split("cursor=")[1].split("&")[0]
        current_response = client.get(
            f"/cursor_events_end_date_offset?cursor={next_cursor}"
        ).json()

    # Should have all events and maintain consistent ordering
    assert len(all_results) == 13
    # Verify no duplicates
    titles = [result["title"] for result in all_results]
    assert len(titles) == len(set(titles))

    # Verify results are sorted by start_dates, then by id (implicit in creation order)
    start_dates = [result["start_date"] for result in all_results]
    assert start_dates == sorted(start_dates), "Results should be sorted by end_date"


def test_cursor_pagination_end_date_offset_backwards():
    """Test cursor pagination handles duplicate end_date values iterating backwards"""

    # Start from the last page by getting all pages first
    response = client.get("/cursor_events_end_date_offset").json()

    # Navigate to the last page
    current_response = response
    while current_response["next"]:
        next_cursor = current_response["next"].split("cursor=")[1].split("&")[0]
        current_response = client.get(
            f"/cursor_events_end_date_offset?cursor={next_cursor}"
        ).json()

    # Now iterate backwards using previous links
    all_results_backwards = []
    while True:
        # Insert at beginning to maintain reverse order
        all_results_backwards = current_response["results"] + all_results_backwards
        if not current_response["previous"]:
            break
        prev_cursor = current_response["previous"].split("cursor=")[1].split("&")[0]
        current_response = client.get(
            f"/cursor_events_end_date_offset?cursor={prev_cursor}"
        ).json()

    # Should have all events and maintain consistent ordering
    assert len(all_results_backwards) == 13
    # Verify no duplicates
    titles = [result["title"] for result in all_results_backwards]
    assert len(titles) == len(set(titles))

    # Verify results are sorted by start_date when iterating backwards
    start_dates = [result["start_date"] for result in all_results_backwards]
    assert start_dates == sorted(
        start_dates
    ), "Results should be sorted by start_date when iterating backwards"


def test_cursor_pagination_default_page_size():
    """Test cursor pagination with default page size."""
    # Create test events

    response = client.get("/cursor_events_default_size").json()

    # Should use default page size which is 1000
    assert len(response["results"]) == 13
    assert response["results"][0]["title"] == "Event 1"
    assert response["results"][-1]["title"] == "Special Event 13"
    assert response["next"] is None
    assert response["previous"] is None


def test_cursor_pagination_custom_page_size_override():
    """Test overriding page size in request."""
    # Create test events

    response = client.get("/cursor_events_default_size?page_size=3").json()

    assert len(response["results"]) == 3
    assert response["results"][0]["title"] == "Event 1"
    assert response["results"][-1]["title"] == "Event 3"
    assert response["next"] is not None
    assert response["previous"] is None


def test_cursor_pagination_with_custom_params():
    """Test cursor pagination with additional query parameters."""

    response = client.get(
        "/cursor_events_with_params?title_filter=Special&page_size=5"
    ).json()

    # Should filter to events with "Special" in title
    assert len(response["results"]) == 3
    assert all("Special" in item["title"] for item in response["results"])


def test_cursor_pagination_invalid_cursor():
    """Test handling of invalid cursor values."""

    response = client.get("/cursor_events?cursor=invalid&page_size=3")

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


def test_cursor_pagination_empty_cursor():
    """Test handling of empty cursor."""

    response = client.get("/cursor_events?cursor=&page_size=3").json()

    # Should default to first page
    assert len(response["results"]) == 3
    assert response["results"][0]["title"] == "Event 1"


def test_cursor_pagination_no_page_size():
    """Test cursor pagination without specifying page_size."""

    response = client.get("/cursor_events").json()

    # Should use default page size from settings
    assert len(response["results"]) >= 1
    assert "next" in response
    assert "previous" in response
    assert "results" in response


def test_cursor_pagination_openapi_schema():
    """Test that cursor pagination generates correct OpenAPI schema."""
    schema = api.get_openapi_schema()["paths"]["/api/cursor_events"]["get"]

    parameters = {param["name"]: param for param in schema["parameters"]}

    # Check page_size parameter
    assert "page_size" in parameters
    page_size_param = parameters["page_size"]
    assert page_size_param["in"] == "query"
    assert page_size_param["required"] is False

    # Check cursor parameter
    assert "cursor" in parameters
    cursor_param = parameters["cursor"]
    assert cursor_param["in"] == "query"
    assert cursor_param["required"] is False
    assert {"type": "string"} in cursor_param["schema"]["anyOf"]
    assert {"type": "null"} in cursor_param["schema"]["anyOf"]


def test_cursor_pagination_response_schema():
    """Test that cursor pagination generates correct response schema."""
    schema = api.get_openapi_schema()["paths"]["/api/cursor_events"]["get"]
    response_schema = schema["responses"][HTTPStatus.OK]["content"]["application/json"][
        "schema"
    ]

    # Should have cursor pagination structure (may be a $ref)
    if "$ref" in response_schema:
        # Extract the schema name and check it exists in components
        ref_path = response_schema["$ref"]
        assert ref_path.startswith("#/components/schemas/")
        schema_name = ref_path.split("/")[-1]
        components_schema = api.get_openapi_schema()["components"]["schemas"][
            schema_name
        ]

        # Check the referenced schema has the right properties
        assert "properties" in components_schema
        properties = components_schema["properties"]
    else:
        # Direct inline schema
        assert "properties" in response_schema
        properties = response_schema["properties"]

    assert "results" in properties
    assert "next" in properties
    assert "previous" in properties

    # Results should be array of items
    assert properties["results"]["type"] == "array"


def test_cursor_pagination_large_page_size():
    """Test edge cases for cursor pagination."""

    # Very large page_size
    response = client.get("/cursor_events?page_size=1000").json()
    # all available items (10 events + 3 special events)
    assert len(response["results"]) == 13
    assert response["next"] is None


def test_cursor_pagination_page_size_of_one():
    # Page size of 1
    response = client.get("/cursor_events?page_size=1").json()
    assert len(response["results"]) == 1
    assert response["results"][0]["title"] == "Event 1"
    assert response["next"] is not None

    # Request all pages and check length and order
    all_results = []
    current_response = response

    while True:
        all_results.extend(current_response["results"])
        if not current_response["next"]:
            break
        next_cursor = current_response["next"].split("cursor=")[1].split("&")[0]
        current_response = client.get(
            f"/cursor_events?cursor={next_cursor}&page_size=1"
        ).json()

    # Check total length
    assert len(all_results) == 13  # 10 events + 3 special events

    # Check order - should be sorted by start_date
    titles = [result["title"] for result in all_results]
    expected_titles = [f"Event {i}" for i in range(1, 11)] + [
        f"Special Event {i}" for i in range(11, 14)
    ]
    assert titles == expected_titles


def test_cursor_pagination_empty_queryset():
    """Test cursor pagination with empty queryset."""
    # Explicitly clear all events for this test
    Category.objects.all().delete()
    Event.objects.all().delete()

    response = client.get("/cursor_events?page_size=5").json()

    assert len(response["results"]) == 0
    assert response["next"] is None
    assert response["previous"] is None


@override_settings(NINJA_PAGINATION_PER_PAGE=20)
def test_cursor_pagination_settings_override():
    """Test that Django settings affect cursor pagination."""

    response = client.get("/cursor_events_default_size").json()
    assert "results" in response
    assert len(response["results"]) == 13


def test_cursor_pagination_deleted_position():
    """Test cursor pagination when the cursor position is deleted between requests."""

    # Get first page with page_size=3 to get a cursor
    first_response = client.get("/cursor_events?page_size=3").json()
    assert len(first_response["results"]) == 3
    assert first_response["next"] is not None

    # Extract the cursor for the next page
    next_cursor = first_response["next"].split("cursor=")[1].split("&")[0]

    # Delete the event that the cursor is pointing to
    # The cursor should be pointing to Event 4
    event_to_delete = Event.objects.get(title="Event 4")
    event_to_delete.delete()

    # Now try to use the cursor - it should still work gracefully
    # even though the position it was pointing to no longer exists
    response = client.get(f"/cursor_events?cursor={next_cursor}&page_size=3").json()

    # Should still return results, just continuing from where it can
    assert len(response["results"]) >= 1
    assert "next" in response
    assert "previous" in response

    # Verify we get the remaining events after the deleted position
    titles = [result["title"] for result in response["results"]]
    assert "Event 4" not in titles
    # Should now contain the deleted Event 5
    assert titles[0] == "Event 5"


def test_cursor_pagination_deleted_position_previous():
    """Test cursor pagination when the cursor position is deleted between requests using previous cursor."""

    # Get to the last page first
    response = client.get("/cursor_events?page_size=3").json()

    # Navigate to get a page with a previous cursor
    while response["next"]:
        next_cursor = response["next"].split("cursor=")[1].split("&")[0]
        response = client.get(f"/cursor_events?cursor={next_cursor}&page_size=3").json()

    # Now we should have a previous cursor
    assert response["previous"] is not None
    prev_cursor = response["previous"].split("cursor=")[1].split("&")[0]

    # Delete an event that will be referenced by the previous cursor

    event_to_delete = Event.objects.get(title="Special Event 13")
    event_to_delete.delete()

    # Now try to use the previous cursor - it should still work gracefully
    # even though the position it was pointing to no longer exists
    prev_response = client.get(
        f"/cursor_events?cursor={prev_cursor}&page_size=3"
    ).json()

    # Should still return results, just continuing from where it can
    assert len(prev_response["results"]) >= 1
    assert "next" in prev_response
    assert "previous" in prev_response

    # Verify we get the remaining events and don't include the deleted one
    titles = [result["title"] for result in prev_response["results"]]
    assert "Special Event 13" not in titles


def test_cursor_pagination_last_item_deleted():
    """Test cursor pagination when the cursor is pointed at the last item, but it is deleted."""

    # Navigate through all pages to get to the last one
    next_cursor = ""

    while True:
        response = client.get(f"/cursor_events?cursor={next_cursor}&page_size=3").json()
        if response["next"] is None:
            break
        next_cursor = response["next"].split("cursor=")[1].split("&")[0]

    # Delete the last item (Special Event 13)
    last_event = Event.objects.get(title="Special Event 13")
    last_event.delete()

    # Now try to use the cursor that was pointing to the last page
    # It should handle the deletion gracefully
    response = client.get(f"/cursor_events?cursor={next_cursor}&page_size=3").json()

    # Should return empty results
    assert len(response["results"]) == 0
    assert response["next"] is None
    assert response["previous"] is not None


# Async versions of all tests


@pytest.mark.asyncio
async def test_async_cursor_pagination_first_page():
    """Test first page of cursor pagination with async."""

    response = await async_client.get("/async_cursor_events?page_size=5")
    response_data = response.json()

    assert len(response_data["results"]) == 5
    assert response_data["results"][0]["title"] == "Event 1"
    assert response_data["results"][-1]["title"] == "Event 5"
    assert response_data["next"] is not None
    assert response_data["previous"] is None


@pytest.mark.asyncio
async def test_async_cursor_pagination_with_cursor():
    """Test navigation using cursor with async."""

    # Get first page to obtain next cursor
    first_response = await async_client.get("/async_cursor_events")
    first_response_data = first_response.json()

    assert len(first_response_data["results"]) == 10
    assert first_response_data["next"] is not None

    if first_response_data["next"]:
        # we can't rely on `next` being a well-formed URL, because the testclient
        # httprequest mock does not pass the path, so we extract the cursor instead
        next_cursor = first_response_data["next"].split("cursor=")[1].split("&")[0]

        # Use cursor to get next page
        response = await async_client.get(f"/async_cursor_events?cursor={next_cursor}")
        response_data = response.json()

        assert len(response_data["results"]) == 3  # Remaining 3 events
        assert response_data["next"] is None
        assert response_data["previous"] is not None


@pytest.mark.asyncio
async def test_async_cursor_pagination_reverse_ordering():
    """Test cursor pagination with reverse ordering with async."""

    response = await async_client.get("/async_cursor_events_reverse")
    response_data = response.json()

    assert len(response_data["results"]) == 10
    # With reverse ordering, should start from the end
    assert response_data["results"][0]["title"] == "Special Event 13"
    assert response_data["next"] is not None
    assert response_data["previous"] is None


@pytest.mark.asyncio
async def test_async_cursor_pagination_end_date_offset():
    """Test cursor pagination handles duplicate end_date values with async"""

    response = await async_client.get("/async_cursor_events_end_date_offset")
    response_data = response.json()

    # Should handle events with same end_date by using id as secondary ordering
    assert len(response_data["results"]) == 2

    # Verify ordering is consistent across pages
    all_results = []
    current_response = response_data

    while True:
        all_results.extend(current_response["results"])
        if not current_response["next"]:
            break
        next_cursor = current_response["next"].split("cursor=")[1].split("&")[0]
        current_response_obj = await async_client.get(
            f"/async_cursor_events_end_date_offset?cursor={next_cursor}"
        )
        current_response = current_response_obj.json()

    # Should have all events and maintain consistent ordering
    assert len(all_results) == 13
    # Verify no duplicates
    titles = [result["title"] for result in all_results]
    assert len(titles) == len(set(titles))

    # Verify results are sorted by start_dates, then by id (implicit in creation order)
    start_dates = [result["start_date"] for result in all_results]
    assert start_dates == sorted(start_dates), "Results should be sorted by end_date"


@pytest.mark.asyncio
async def test_async_cursor_pagination_end_date_offset_backwards():
    """Test cursor pagination handles duplicate end_date values iterating backwards with async"""

    # Start from the last page by getting all pages first
    response = await async_client.get("/async_cursor_events_end_date_offset")
    response_data = response.json()

    # Navigate to the last page
    current_response = response_data
    while current_response["next"]:
        next_cursor = current_response["next"].split("cursor=")[1].split("&")[0]
        current_response_obj = await async_client.get(
            f"/async_cursor_events_end_date_offset?cursor={next_cursor}"
        )
        current_response = current_response_obj.json()

    # Now iterate backwards using previous links
    all_results_backwards = []
    while True:
        # Insert at beginning to maintain reverse order
        all_results_backwards = current_response["results"] + all_results_backwards
        if not current_response["previous"]:
            break
        prev_cursor = current_response["previous"].split("cursor=")[1].split("&")[0]
        current_response_obj = await async_client.get(
            f"/async_cursor_events_end_date_offset?cursor={prev_cursor}"
        )
        current_response = current_response_obj.json()

    # Should have all events and maintain consistent ordering
    assert len(all_results_backwards) == 13
    # Verify no duplicates
    titles = [result["title"] for result in all_results_backwards]
    assert len(titles) == len(set(titles))

    # Verify results are sorted by start_date when iterating backwards
    start_dates = [result["start_date"] for result in all_results_backwards]
    assert start_dates == sorted(
        start_dates
    ), "Results should be sorted by start_date when iterating backwards"


@pytest.mark.asyncio
async def test_async_cursor_pagination_default_page_size():
    """Test cursor pagination with default page size with async."""
    # Create test events

    response = await async_client.get("/async_cursor_events_default_size")
    response_data = response.json()

    # Should use default page size which is 1000
    assert len(response_data["results"]) == 13
    assert response_data["results"][0]["title"] == "Event 1"
    assert response_data["results"][-1]["title"] == "Special Event 13"
    assert response_data["next"] is None
    assert response_data["previous"] is None


@pytest.mark.asyncio
async def test_async_cursor_pagination_custom_page_size_override():
    """Test overriding page size in request with async."""
    # Create test events

    response = await async_client.get("/async_cursor_events_default_size?page_size=3")
    response_data = response.json()

    assert len(response_data["results"]) == 3
    assert response_data["results"][0]["title"] == "Event 1"
    assert response_data["results"][-1]["title"] == "Event 3"
    assert response_data["next"] is not None
    assert response_data["previous"] is None


@pytest.mark.asyncio
async def test_async_cursor_pagination_with_custom_params():
    """Test cursor pagination with additional query parameters with async."""

    response = await async_client.get(
        "/async_cursor_events_with_params?title_filter=Special&page_size=5"
    )
    response_data = response.json()

    # Should filter to events with "Special" in title
    assert len(response_data["results"]) == 3
    assert all("Special" in item["title"] for item in response_data["results"])


@pytest.mark.asyncio
async def test_async_cursor_pagination_invalid_cursor():
    """Test handling of invalid cursor values with async."""

    response = await async_client.get("/async_cursor_events?cursor=invalid&page_size=3")

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_async_cursor_pagination_empty_cursor():
    """Test handling of empty cursor with async."""

    response = await async_client.get("/async_cursor_events?cursor=&page_size=3")
    response_data = response.json()

    # Should default to first page
    assert len(response_data["results"]) == 3
    assert response_data["results"][0]["title"] == "Event 1"


@pytest.mark.asyncio
async def test_async_cursor_pagination_no_page_size():
    """Test cursor pagination without specifying page_size with async."""

    response = await async_client.get("/async_cursor_events")
    response_data = response.json()

    # Should use default page size from settings
    assert len(response_data["results"]) >= 1
    assert "next" in response_data
    assert "previous" in response_data
    assert "results" in response_data


@pytest.mark.asyncio
async def test_async_cursor_pagination_large_page_size():
    """Test edge cases for cursor pagination with async."""

    # Very large page_size
    response = await async_client.get("/async_cursor_events?page_size=1000")
    response_data = response.json()
    # all available items (10 events + 3 special events)
    assert len(response_data["results"]) == 13
    assert response_data["next"] is None


@pytest.mark.asyncio
async def test_async_cursor_pagination_page_size_of_one():
    # Page size of 1 with async
    response = await async_client.get("/async_cursor_events?page_size=1")
    response_data = response.json()
    assert len(response_data["results"]) == 1
    assert response_data["results"][0]["title"] == "Event 1"
    assert response_data["next"] is not None

    # Request all pages and check length and order
    all_results = []
    current_response = response_data

    while True:
        all_results.extend(current_response["results"])
        if not current_response["next"]:
            break
        next_cursor = current_response["next"].split("cursor=")[1].split("&")[0]
        current_response_obj = await async_client.get(
            f"/async_cursor_events?cursor={next_cursor}&page_size=1"
        )
        current_response = current_response_obj.json()

    # Check total length
    assert len(all_results) == 13  # 10 events + 3 special events

    # Check order - should be sorted by start_date
    titles = [result["title"] for result in all_results]
    expected_titles = [f"Event {i}" for i in range(1, 11)] + [
        f"Special Event {i}" for i in range(11, 14)
    ]
    assert titles == expected_titles


@pytest.mark.asyncio
async def test_async_cursor_pagination_empty_queryset():
    """Test cursor pagination with empty queryset with async."""
    # Explicitly clear all events for this test using async-safe methods
    await Category.objects.all().adelete()
    await Event.objects.all().adelete()

    response = await async_client.get("/async_cursor_events?page_size=5")
    response_data = response.json()

    assert len(response_data["results"]) == 0
    assert response_data["next"] is None
    assert response_data["previous"] is None


@pytest.mark.asyncio
@override_settings(NINJA_PAGINATION_PER_PAGE=20)
async def test_async_cursor_pagination_settings_override():
    """Test that Django settings affect cursor pagination with async."""

    response = await async_client.get("/async_cursor_events_default_size")
    response_data = response.json()
    assert "results" in response_data
    assert len(response_data["results"]) == 13


@pytest.mark.asyncio
async def test_async_cursor_pagination_deleted_position():
    """Test cursor pagination when the cursor position is deleted between requests with async."""

    # Get first page with page_size=3 to get a cursor
    first_response = await async_client.get("/async_cursor_events?page_size=3")
    first_response_data = first_response.json()
    assert len(first_response_data["results"]) == 3
    assert first_response_data["next"] is not None

    # Extract the cursor for the next page
    next_cursor = first_response_data["next"].split("cursor=")[1].split("&")[0]

    # Delete the event that the cursor is pointing to
    # The cursor should be pointing to Event 4
    event_to_delete = await Event.objects.aget(title="Event 4")
    await event_to_delete.adelete()

    # Now try to use the cursor - it should still work gracefully
    # even though the position it was pointing to no longer exists
    response = await async_client.get(
        f"/async_cursor_events?cursor={next_cursor}&page_size=3"
    )
    response_data = response.json()

    # Should still return results, just continuing from where it can
    assert len(response_data["results"]) >= 1
    assert "next" in response_data
    assert "previous" in response_data

    # Verify we get the remaining events after the deleted position
    titles = [result["title"] for result in response_data["results"]]
    assert "Event 4" not in titles
    # Should now contain the deleted Event 5
    assert titles[0] == "Event 5"


@pytest.mark.asyncio
async def test_async_cursor_pagination_deleted_position_previous():
    """Test cursor pagination when the cursor position is deleted between requests using previous cursor with async."""

    # Get to the last page first
    response = await async_client.get("/async_cursor_events?page_size=3")
    response_data = response.json()

    # Navigate to get a page with a previous cursor
    while response_data["next"]:
        next_cursor = response_data["next"].split("cursor=")[1].split("&")[0]
        response = await async_client.get(
            f"/async_cursor_events?cursor={next_cursor}&page_size=3"
        )
        response_data = response.json()

    # Now we should have a previous cursor
    assert response_data["previous"] is not None
    prev_cursor = response_data["previous"].split("cursor=")[1].split("&")[0]

    # Delete an event that will be referenced by the previous cursor

    event_to_delete = await Event.objects.aget(title="Special Event 13")
    await event_to_delete.adelete()

    # Now try to use the previous cursor - it should still work gracefully
    # even though the position it was pointing to no longer exists
    prev_response = await async_client.get(
        f"/async_cursor_events?cursor={prev_cursor}&page_size=3"
    )
    prev_response_data = prev_response.json()

    # Should still return results, just continuing from where it can
    assert len(prev_response_data["results"]) >= 1
    assert "next" in prev_response_data
    assert "previous" in prev_response_data

    # Verify we get the remaining events and don't include the deleted one
    titles = [result["title"] for result in prev_response_data["results"]]
    assert "Special Event 13" not in titles


@pytest.mark.asyncio
async def test_async_cursor_pagination_last_item_deleted():
    """Test cursor pagination when the cursor is pointed at the last item, but it is deleted with async."""

    # Navigate through all pages to get to the last one
    next_cursor = ""

    while True:
        response = await async_client.get(
            f"/async_cursor_events?cursor={next_cursor}&page_size=3"
        )
        response_data = response.json()
        if response_data["next"] is None:
            break
        next_cursor = response_data["next"].split("cursor=")[1].split("&")[0]

    # Delete the last item (Special Event 13)
    last_event = await Event.objects.aget(title="Special Event 13")
    await last_event.adelete()

    # Now try to use the cursor that was pointing to the last page
    # It should handle the deletion gracefully
    response = await async_client.get(
        f"/async_cursor_events?cursor={next_cursor}&page_size=3"
    )
    response_data = response.json()

    # Should return empty results
    assert len(response_data["results"]) == 0
    assert response_data["next"] is None
    assert response_data["previous"] is not None
