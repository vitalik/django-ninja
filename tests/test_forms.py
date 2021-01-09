from ninja import NinjaAPI, Form
from client import NinjaClient


api = NinjaAPI()


@api.post("/form")
def form_operation(request, s: str = Form(...), i: int = Form(...)):
    return {"s": s, "i": i}


client = NinjaClient(api)


def test_form():
    response = client.post("/form")  # invalid
    assert response.status_code == 422

    response = client.post("/form", POST={"s": "text", "i": 2})
    assert response.status_code == 200
    assert response.json() == {"i": 2, "s": "text"}


def test_schema():
    schema = api.get_openapi_schema()
    method = schema["paths"]["/api/form"]["post"]
    assert method["requestBody"] == {
        "content": {
            "application/x-www-form-urlencoded": {
                "schema": {
                    "properties": {
                        "i": {"title": "I", "type": "integer"},
                        "s": {"title": "S", "type": "string"},
                    },
                    "required": ["s", "i"],
                    "title": "FormParams",
                    "type": "object",
                }
            }
        },
        "required": True,
    }


# TODO: Fix schema for this case:
# class Credentials(Schema):
#     username: str
#     password: str


# @api.post("/login")
# def login(request, credentials: Credentials = Form(...)):
#     return {'username': credentials.username}
