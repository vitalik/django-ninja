from uuid import UUID

from django.urls import register_converter

from ninja import Field, Path, Query, Router, Schema

router = Router()


@router.get("/text")
def get_text(request):
    return "Hello World"


@router.get("/path/{item_id}")
def get_id(request, item_id):
    return item_id


@router.get("/path/str/{item_id}")
def get_str_id(request, item_id: str):
    return item_id


@router.get("/path/int/{item_id}")
def get_int_id(request, item_id: int):
    return item_id


@router.get("/path/float/{item_id}")
def get_float_id(request, item_id: float):
    return item_id


@router.get("/path/bool/{item_id}")
def get_bool_id(request, item_id: bool):
    return item_id


@router.get("/path/param/{item_id}")
def get_path_param_id(request, item_id: str = Path(None)):
    return item_id


@router.get("/path/param-required/{item_id}")
def get_path_param_required_id(request, item_id: str = Path(...)):
    return item_id


@router.get("/path/param-minlength/{item_id}")
def get_path_param_min_length(request, item_id: str = Path(..., min_length=3)):
    return item_id


@router.get("/path/param-maxlength/{item_id}")
def get_path_param_max_length(request, item_id: str = Path(..., max_length=3)):
    return item_id


@router.get("/path/param-min_maxlength/{item_id}")
def get_path_param_min_max_length(
    request, item_id: str = Path(..., max_length=3, min_length=2)
):
    return item_id


@router.get("/path/param-gt/{item_id}")
def get_path_param_gt(request, item_id: float = Path(..., gt=3)):
    return item_id


@router.get("/path/param-gt0/{item_id}")
def get_path_param_gt0(request, item_id: float = Path(..., gt=0)):
    return item_id


@router.get("/path/param-ge/{item_id}")
def get_path_param_ge(request, item_id: float = Path(..., ge=3)):
    return item_id


@router.get("/path/param-lt/{item_id}")
def get_path_param_lt(request, item_id: float = Path(..., lt=3)):
    return item_id


@router.get("/path/param-lt0/{item_id}")
def get_path_param_lt0(request, item_id: float = Path(..., lt=0)):
    return item_id


@router.get("/path/param-le/{item_id}")
def get_path_param_le(request, item_id: float = Path(..., le=3)):
    return item_id


@router.get("/path/param-lt-gt/{item_id}")
def get_path_param_lt_gt(request, item_id: float = Path(..., lt=3, gt=1)):
    return item_id


@router.get("/path/param-le-ge/{item_id}")
def get_path_param_le_ge(request, item_id: float = Path(..., le=3, ge=1)):
    return item_id


@router.get("/path/param-lt-int/{item_id}")
def get_path_param_lt_int(request, item_id: int = Path(..., lt=3)):
    return item_id


@router.get("/path/param-gt-int/{item_id}")
def get_path_param_gt_int(request, item_id: int = Path(..., gt=3)):
    return item_id


@router.get("/path/param-le-int/{item_id}")
def get_path_param_le_int(request, item_id: int = Path(..., le=3)):
    return item_id


@router.get("/path/param-ge-int/{item_id}")
def get_path_param_ge_int(request, item_id: int = Path(..., ge=3)):
    return item_id


@router.get("/path/param-lt-gt-int/{item_id}")
def get_path_param_lt_gt_int(request, item_id: int = Path(..., lt=3, gt=1)):
    return item_id


@router.get("/path/param-le-ge-int/{item_id}")
def get_path_param_le_ge_int(request, item_id: int = Path(..., le=3, ge=1)):
    return item_id


@router.get("/path/param-django-str/{str:item_id}")
def get_path_param_django_str(request, item_id):
    return item_id


@router.get("/path/param-django-int/{int:item_id}")
def get_path_param_django_int(request, item_id: int):
    assert isinstance(item_id, int)
    return item_id


@router.get("/path/param-django-int/not-an-int")
def get_path_param_django_not_an_int(request):
    """Verify that url resolution for get_path_param_django_int passes non-ints forward"""
    return "Found not-an-int"


@router.get("/path/param-django-int-str/{int:item_id}")
def get_path_param_django_int_str(request, item_id: str):
    assert isinstance(item_id, str)
    return item_id


@router.get("/path/param-django-slug/{slug:item_id}")
def get_path_param_django_slug(request, item_id):
    return item_id


@router.get("/path/param-django-uuid/{uuid:item_id}")
def get_path_param_django_uuid(request, item_id: UUID):
    assert isinstance(item_id, UUID)
    return item_id


@router.get("/path/param-django-uuid-str/{uuid:item_id}")
def get_path_param_django_uuid_str(request, item_id):
    assert isinstance(item_id, str)
    return item_id


@router.get("/path/param-django-path/{path:item_id}/after")
def get_path_param_django_path(request, item_id):
    return item_id


@router.get("/query")
def get_query(request, query):
    return f"foo bar {query}"


@router.get("/query/optional")
def get_query_optional(request, query=None):
    if query is None:
        return "foo bar"
    return f"foo bar {query}"


@router.get("/query/int")
def get_query_type(request, query: int):
    return f"foo bar {query}"


@router.get("/query/int/optional")
def get_query_type_optional(request, query: int = None):
    if query is None:
        return "foo bar"
    return f"foo bar {query}"


@router.get("/query/int/default")
def get_query_type_optional_10(request, query: int = 10):
    return f"foo bar {query}"


@router.get("/query/param")
def get_query_param(request, query=Query(None)):
    if query is None:
        return "foo bar"
    return f"foo bar {query}"


@router.get("/query/param-required")
def get_query_param_required(request, query=Query(...)):
    return f"foo bar {query}"


@router.get("/query/param-required/int")
def get_query_param_required_type(request, query: int = Query(...)):
    return f"foo bar {query}"


class AliasedSchema(Schema):
    query: str = Field(..., alias="aliased.-_~name")


@router.get("/query/aliased-name")
def get_query_aliased_name(request, query: AliasedSchema = Query(...)):
    return f"foo bar {query.query}"


class CustomPathConverter1:
    regex = "[0-9]+"

    def to_python(self, value) -> "int":
        """reverse the string and convert to int"""
        return int(value[::-1])

    def to_url(self, value):
        return str(value)


class CustomPathConverter2:
    regex = "[0-9]+"

    def to_python(self, value):
        """reverse the string and convert to float like"""
        return f"0.{value[::-1]}"

    def to_url(self, value):
        return str(value)


register_converter(CustomPathConverter1, "custom-int")
register_converter(CustomPathConverter2, "custom-float")


@router.get("/path/param-django-custom-int/{custom-int:item_id}")
def get_path_param_django_custom_int(request, item_id: int):
    return item_id


@router.get("/path/param-django-custom-float/{custom-float:item_id}")
def get_path_param_django_custom_float(request, item_id: float):
    return item_id
