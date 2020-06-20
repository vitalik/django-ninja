from datetime import date
from ninja import Router
from typing import List
from pydantic import BaseModel
from django.shortcuts import get_object_or_404
from .models import Event

router = Router()


class EventSchema(BaseModel):
    title: str
    start_date: date
    end_date: date

    class Config:
        orm_mode = True


@router.post("/create")
def create_event(request, event: EventSchema):
    Event.objects.create(**event.dict())
    return event


@router.get("")
def list_events(request) -> List[EventSchema]:
    return list(Event.objects.all())


@router.get("/{id}")
def get_event(request, id: int) -> EventSchema:
    event = get_object_or_404(Event, id=id)
    return event
