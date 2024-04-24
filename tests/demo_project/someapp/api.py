from datetime import date
from typing import List

from django.shortcuts import get_object_or_404
from pydantic import BaseModel

from ninja import Router
from ninja.pagination import CursorPagination, paginate

from .models import Category, Event

router = Router()


class EventSchema(BaseModel):
    title: str
    start_date: date
    end_date: date

    class Config:
        from_attributes = True


class CategorySchema(BaseModel):
    title: str

    class Config:
        from_attributes = True


@router.get("/categories", response=List[CategorySchema])
@paginate(CursorPagination)
def list_categories(request):
    return Category.objects.order_by("title")


@router.post("/create", url_name="event-create-url-name")
def create_event(request, event: EventSchema):
    Event.objects.create(**event.model_dump())
    return event


@router.get("", response=List[EventSchema])
def list_events(request):
    return list(Event.objects.all())


@router.delete("")
def delete_events(request):
    Event.objects.all().delete()


@router.get("/{id}", response=EventSchema)
def get_event(request, id: int):
    event = get_object_or_404(Event, id=id)
    return event
