from django.db import models
from pydantic.experimental.missing_sentinel import MISSING

from ninja import Field, NinjaAPI, Schema
from ninja.orm import create_schema


class Project(models.Model):
    name = models.CharField(max_length=10)
    missing = models.CharField(max_length=10, blank=True, null=True)

    class Meta:
        app_label = "tests"


ProjectModelSchema = create_schema(
    Project, fields=["name", "missing"], nullable_value=MISSING, nullable_type=MISSING
)


class ProjectSchema(Schema):
    name: str = Field(..., max_length=10)
    missing: str | MISSING = Field(MISSING, max_length=10)


api = NinjaAPI()


@api.get("/modelschema", response=ProjectModelSchema)
def get_modelschema(request, input: ProjectModelSchema):
    return Project(name="Name")


@api.get("/schema", response=ProjectSchema)
def get_schema(request, input: ProjectSchema):
    return {"name": "Name"}


openapi_schema = api.get_openapi_schema()


def test_missing_in_schema():
    assert (
        "missing"
        not in openapi_schema["components"]["schemas"]["ProjectSchema"]["required"]
    )
    assert openapi_schema["components"]["schemas"]["ProjectSchema"]["properties"][
        "missing"
    ] == {"title": "Missing", "type": "string", "maxLength": 10}
    assert ProjectSchema(name="Name").model_dump() == {"name": "Name"}


def test_missing_in_modelschema():
    assert (
        "missing" not in openapi_schema["components"]["schemas"]["Project"]["required"]
    )
    assert openapi_schema["components"]["schemas"]["Project"]["properties"][
        "missing"
    ] == {"title": "Missing", "type": "string", "maxLength": 10}
    assert ProjectModelSchema(name="Name").model_dump() == {"name": "Name"}
