from ninja import Router, Query, Path


router = Router()


@router.get("/text")
def get_text(request,):
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
