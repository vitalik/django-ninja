import datetime

from django.db import models
from pydantic import ConfigDict
from pydantic.alias_generators import to_camel

from ninja import Field, ModelSchema, NinjaAPI, Schema


class SchemaWithAlias(Schema):
    foo: str = Field("", alias="bar")


api = NinjaAPI()


@api.get("/path", response=SchemaWithAlias)
def alias_operation(request):
    return {"bar": "value"}


def test_alias():
    schema = api.get_openapi_schema()["components"]
    print(schema)
    assert schema == {
        "schemas": {
            "SchemaWithAlias": {
                "type": "object",
                "properties": {
                    "foo": {"type": "string", "default": "", "title": "Foo"}
                },
                "title": "SchemaWithAlias",
            }
        }
    }


# TODO: check the conflicting approach
#       when alias is used both for response and request schema
#       basically it need to generate 2 schemas - one with alias another without
# @api.post("/path", response=SchemaWithAlias)
# def alias_operation(request, payload: SchemaWithAlias):
#     return {"bar": payload.foo}


def test_alias_foreignkey_schema():
    class Author(models.Model):
        id = models.AutoField(primary_key=True)
        name = models.CharField(max_length=50)

        class Meta:
            app_label = "tests"

    class Book(models.Model):
        id = models.AutoField(primary_key=True)
        name = models.CharField(max_length=100)
        author = models.ForeignKey(Author, on_delete=models.CASCADE)
        published_date = models.DateField(default=datetime.date.today())

        class Meta:
            app_label = "tests"

    class BookSchema(ModelSchema):
        model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

        class Meta:
            model = Book
            fields = "__all__"

    assert BookSchema.json_schema() == {
        "properties": {
            "authorId": {"title": "Author", "type": "integer"},
            "id": {"anyOf": [{"type": "integer"}, {"type": "null"}], "title": "Id"},
            "name": {"maxLength": 100, "title": "Name", "type": "string"},
            "publishedDate": {
                "default": "2024-03-22",
                "format": "date",
                "title": "Published Date",
                "type": "string",
            },
        },
        "required": ["name", "authorId"],
        "title": "BookSchema",
        "type": "object",
    }


def test_alias_foreignkey_property():
    class Author(models.Model):
        id = models.AutoField(primary_key=True)
        name = models.CharField(max_length=50)

        class Meta:
            app_label = "tests"

    class Book(models.Model):
        id = models.AutoField(primary_key=True)
        name = models.CharField(max_length=100)
        author = models.ForeignKey(Author, on_delete=models.CASCADE)
        published_date = models.DateField(default=datetime.date.today())

        class Meta:
            app_label = "tests"

    class BookSchema(ModelSchema):
        model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

        class Meta:
            model = Book
            fields = "__all__"

    author_test = Author(name="J. R. R. Tolkien", id=1)
    model_test = Book(author=author_test, name="The Hobbit", id=1)
    schema_test = BookSchema.from_orm(model_test)

    schema_test.author = 2
    assert schema_test.author == 2
