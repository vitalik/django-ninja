from django.db import models
from ninja import ModelSchema


def test_simple():
    class User(models.Model):
        firstname = models.CharField()
        lastname = models.CharField(blank=True, null=True)

        class Meta:
            app_label = "tests"

    class SampleSchema(ModelSchema):
        class Config:
            model = User
            model_fields = ["firstname", "lastname"]

        def hello(self):
            return f"Hello({self.firstname})"

    print(SampleSchema.schema())
    assert SampleSchema.schema() == {
        "title": "SampleSchema",
        "type": "object",
        "properties": {
            "firstname": {"title": "Firstname", "type": "string"},
            "lastname": {"title": "Lastname", "type": "string"},
        },
        "required": ["firstname"],
    }

    assert SampleSchema(firstname="ninja").hello() == "Hello(ninja)"


def test_custom():
    class CustomModel(models.Model):
        f1 = models.CharField()
        f2 = models.CharField(blank=True, null=True)

        class Meta:
            app_label = "tests"

    class CustomSchema(ModelSchema):
        f3: int
        f4: int = 1
        f5 = ""  # not annotated should be ignored
        _private: str = "<secret>"  # private should be ignored

        class Config:
            model = CustomModel
            model_fields = ["f1", "f2"]

    print(CustomSchema.schema())
    assert CustomSchema.schema() == {
        "title": "CustomSchema",
        "type": "object",
        "properties": {
            "f1": {"title": "F1", "type": "string"},
            "f2": {"title": "F2", "type": "string"},
            "f3": {"title": "F3", "type": "integer"},
            "f4": {"title": "F4", "default": 1, "type": "integer"},
        },
        "required": ["f1", "f3"],
    }
