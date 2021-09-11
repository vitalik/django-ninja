from ninja import NinjaAPI

api = NinjaAPI()


@api.get("/operation1", operation_id="my_id")
def operation_1(request):
    """
    This will be in description
    """
    return {"docstrings": True}


@api.get("/operation2", description="description from argument", deprecated=True)
def operation2(request):
    return {"description": True, "deprecated": True}


@api.get("/operation3", summary="Summary from argument", description="description arg")
def operation3(request):
    "This one also has docstring description"
    return {"summary": True, "description": "multiple"}


@api.get("/operation4", tags=["tag1", "tag2"])
def operation4(request):
    return {"tags": True}


@api.get("/not-included", include_in_schema=False)
def not_included(request):
    return True


schema = api.get_openapi_schema()


def test_schema():
    op1 = schema["paths"]["/api/operation1"]["get"]
    op2 = schema["paths"]["/api/operation2"]["get"]
    op3 = schema["paths"]["/api/operation3"]["get"]
    op4 = schema["paths"]["/api/operation4"]["get"]

    assert op1["operationId"] == "my_id"
    assert op2["operationId"] == "test_openapi_params_operation2"
    assert op3["operationId"] == "test_openapi_params_operation3"
    assert op4["operationId"] == "test_openapi_params_operation4"

    assert op1["summary"] == "Operation 1"
    assert op2["summary"] == "Operation2"
    assert op3["summary"] == "Summary from argument"
    assert op4["summary"] == "Operation4"

    assert op1["description"] == "This will be in description"

    assert op2["description"] == "description from argument"
    assert op2["deprecated"] is True

    assert op3["description"] == "description arg"

    assert op4["tags"] == ["tag1", "tag2"]


def test_not_included():
    assert list(schema["paths"].keys()) == [
        "/api/operation1",
        "/api/operation2",
        "/api/operation3",
        "/api/operation4",
    ]
    # checking that "/not-included" is not there
