from datetime import date
from typing import List

from django.shortcuts import get_object_or_404
from pydantic import BaseModel

from ninja import Router
from ninja.schema import Schema

from .models import Event

router = Router()


class EventSchema(BaseModel):
    title: str
    start_date: date
    end_date: date

    class Config:
        orm_mode = True


@router.post("/create", url_name="event-create-url-name")
def create_event(request, event: EventSchema):
    Event.objects.create(**event.dict())
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


class EventSchemaWithPeriod(Schema):
    title: str
    start_date: date
    end_date: date
    period: str

    def resolve_period(self, obj):
        return f"{obj.start_date} - {obj.end_date}"


@router.get("/{id}/with-period-dict", response=EventSchemaWithPeriod)
def get_event_with_period_dict(request, id: int):
    event = get_object_or_404(Event, id=id)
    return {"title": event.title, "start_date": event.start_date, "end_date": event.end_date}


@router.get("/{id}/with-period-model", response=EventSchemaWithPeriod)
def get_event_with_period_model(request, id: int):
    event = get_object_or_404(Event, id=id)
    return event
