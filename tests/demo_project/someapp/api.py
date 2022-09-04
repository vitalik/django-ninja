from datetime import date
from typing import List, Optional

from django.shortcuts import get_object_or_404

from ninja import Router, Field, Schema

from .models import Event, Category

router = Router()


class EventSchema(Schema):
    title: str
    start_date: date
    end_date: date
    category: Optional[str] = Field(None, alias="category.title")

    class Config:
        orm_mode = True


@router.post("/create", url_name="event-create-url-name", response=EventSchema)
def create_event(request, event: EventSchema):
    payload = event.dict()
    category_title = payload.pop('category')
    
    if category_title is not None:
        category, created = Category.objects.get_or_create(title=category_title)
    else:
        category = None

    return Event.objects.create(category=category, **payload)


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
