from django.db import models
from pydantic.experimental.missing_sentinel import MISSING

from ninja import Field, ModelSchema, NinjaAPI, Schema
from ninja.orm import create_schema


class Status(models.Model):
    label = models.CharField(max_length=10)
    missing = models.CharField(max_length=10, blank=True, null=True)

    class Meta:
        app_label = "tests"


class Project(models.Model):
    name = models.CharField(max_length=10)
    missing = models.CharField(max_length=10, blank=True, null=True)
    status = models.ForeignKey(Status, on_delete=models.SET_NULL, blank=True, null=True)

    class Meta:
        app_label = "tests"


ProjectModelSchema = create_schema(
    Project,
    fields=["name", "missing", "status"],
    nullable_value=MISSING,
    nullable_type=MISSING,
    depth=2,
)


class ProjectModelSchemaClass(ModelSchema):
    class Meta:
        model = Project
        fields = ["name", "missing"]
        nullable_type = MISSING
        nullable_value = MISSING


class ProjectSchema(Schema):
    name: str = Field(..., max_length=10)
    missing: str | MISSING = Field(MISSING, max_length=10)


api = NinjaAPI()


@api.get("/modelschema", response=ProjectModelSchema)
def get_modelschema(request, input: ProjectModelSchema):
    return Project(name="Name")


@api.get("/modelschemameta", response=ProjectModelSchemaClass)
def get_modelschemameta(request, input: ProjectModelSchemaClass):
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

    # the configured `nullable_value`, `None`s, and empty lists should be converted to `nullable_value`
    assert ProjectModelSchema(name="Name", missing=None).model_dump() == {
        "name": "Name"
    }
    assert ProjectModelSchema(name="Name", missing=MISSING).model_dump() == {
        "name": "Name"
    }
    assert ProjectModelSchema(name="Name", missing=[]).model_dump() == {"name": "Name"}


def test_missing_in_meta():
    assert (
        "missing"
        not in openapi_schema["components"]["schemas"]["ProjectModelSchemaClass"][
            "required"
        ]
    )
    assert openapi_schema["components"]["schemas"]["ProjectModelSchemaClass"][
        "properties"
    ]["missing"] == {"title": "Missing", "type": "string", "maxLength": 10}

    assert ProjectModelSchemaClass(name="Name").model_dump() == {"name": "Name"}

    # the configured `nullable_value`, `None`s, and empty lists should be converted to `nullable_value`
    assert ProjectModelSchemaClass(name="Name", missing=None).model_dump() == {
        "name": "Name"
    }
    assert ProjectModelSchemaClass(name="Name", missing=MISSING).model_dump() == {
        "name": "Name"
    }
    assert ProjectModelSchemaClass(name="Name", missing=[]).model_dump() == {
        "name": "Name"
    }


def test_missing_in_child():
    assert (
        "missing" not in openapi_schema["components"]["schemas"]["Status"]["required"]
    )
    assert openapi_schema["components"]["schemas"]["Status"]["properties"][
        "missing"
    ] == {"title": "Missing", "type": "string", "maxLength": 10}

    inst = ProjectModelSchema(name="Name", status=Status(label="Label"))
    assert inst.model_dump() == {"name": "Name", "status": {"label": "Label"}}

    # the configured `nullable_value`, `None`s, and empty lists should be converted to `nullable_value`
    inst = ProjectModelSchema(name="Name", status=Status(label="Label", missing=None))
    assert inst.model_dump() == {"name": "Name", "status": {"label": "Label"}}
    inst = ProjectModelSchema(
        name="Name", status=Status(label="Label", missing=MISSING)
    )
    assert inst.model_dump() == {"name": "Name", "status": {"label": "Label"}}
    inst = ProjectModelSchema(name="Name", status=Status(label="Label", missing=[]))
    assert inst.model_dump() == {"name": "Name", "status": {"label": "Label"}}
