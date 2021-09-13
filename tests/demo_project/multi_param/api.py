"""Test App to use with Swagger UI and in unit tests"""

from ninja import (
    Body,
    Cookie,
    File,
    Form,
    Header,
    Path,
    Query,
    Router,
    Schema,
    UploadedFile,
)

router = Router()


def to_kebab(string: str) -> str:
    return string.replace("_", "-")


class TestData4(Schema):
    foo4: int = 44
    bar4: str = "44bar"


class TestData3(Schema):
    foo3: int
    bar3: str = "33bar"


class TestData2(Schema):
    foo2: int = 22
    bar2: str
    d3: TestData3


class TestData(Schema):
    foo: int
    bar: str = "11bar"
    d2: TestData2


class ResponseData(Schema):
    i: int
    s: str
    data: TestData4
    nested_data: TestData

    class Config(Schema.Config):
        alias_generator = to_kebab
        allow_population_by_field_name = True


@router.post("/test-multi-query", response=ResponseData, by_alias=True)
def test_multi_query(
    request,
    i: int = Query(...),
    s: str = Query("a-str"),
    data: TestData4 = Query(...),
    nested_data: TestData = Query(..., alias="nested-data"),
):
    return dict(s=s, i=i, data=data, nested_data=nested_data)


@router.post(
    "/test-multi-path/{i}/{s}/{foo4}/{bar4}/{foo}/{bar}/{foo2}/{bar2}/{foo3}/{bar3}/",
    response=ResponseData,
    by_alias=True,
)
def test_multi_path(
    request,
    i: int = Path(...),
    s: str = Path("a-str"),
    data: TestData4 = Path(...),
    nested_data: TestData = Path(..., alias="nested-data"),
):
    return dict(s=s, i=i, data=data, nested_data=nested_data)


@router.post("/test-multi-header", response=ResponseData, by_alias=True)
def test_multi_header(
    request,
    i: int = Header(...),
    s: str = Header("a-str"),
    data: TestData4 = Header(...),
    nested_data: TestData = Header(..., alias="nested-data"),
):
    return dict(s=s, i=i, data=data, nested_data=nested_data)


@router.post("/test-multi-cookie", response=ResponseData, by_alias=True)
def test_multi_cookie(
    request,
    i: int = Cookie(...),
    s: str = Cookie("a-str"),
    data: TestData4 = Cookie(...),
    nested_data: TestData = Cookie(..., alias="nested-data"),
):
    """Testing w/ Cookies requires setting the cookies by hand in the browser inspector"""
    return dict(s=s, i=i, data=data, nested_data=nested_data)


@router.post("/test-multi-form", response=ResponseData, by_alias=True)
def test_multi_form(
    request,
    i: int = Form(...),
    s: str = Form("a-str"),
    data: TestData4 = Form(...),
    nested_data: TestData = Form(..., alias="nested-data"),
):
    return dict(s=s, i=i, data=data, nested_data=nested_data)


@router.post("/test-multi-body", response=ResponseData, by_alias=True)
def test_multi_body(
    request,
    i: int = Body(...),
    s: str = Body("a-str"),
    data: TestData4 = Body(...),
    nested_data: TestData = Body(..., alias="nested-data"),
):
    return dict(s=s, i=i, data=data, nested_data=nested_data)


@router.post("/test-multi-body-file", response=ResponseData, by_alias=True)
def test_multi_body_file(
    request,
    file: UploadedFile,
    i: int = Body(...),
    s: str = Body("a-str"),
    data: TestData4 = Body(...),
    nested_data: TestData = Body(..., alias="nested-data"),
):
    return dict(s=s, i=i, data=data, nested_data=nested_data)


@router.post("/test-multi-form-file", response=ResponseData, by_alias=True)
def test_multi_form_file(
    request,
    file: UploadedFile,
    i: int = Form(...),
    s: str = Form("a-str"),
    data: TestData4 = Form(...),
    nested_data: TestData = Form(..., alias="nested-data"),
):
    return dict(s=s, i=i, data=data, nested_data=nested_data)


@router.post("/test-multi-body-form", response=ResponseData, by_alias=True)
def test_multi_body_form(
    request,
    i: int = Body(...),
    s: str = Form("a-str"),
    data: TestData4 = Body(...),
    nested_data: TestData = Form(..., alias="nested-data"),
):
    return dict(s=s, i=i, data=data, nested_data=nested_data)


@router.post("/test-multi-form-body", response=ResponseData, by_alias=True)
def test_multi_form_body(
    request,
    i: int = Form(...),
    s: str = Body("a-str"),
    data: TestData4 = Form(...),
    nested_data: TestData = Body(..., alias="nested-data"),
):
    return dict(s=s, i=i, data=data, nested_data=nested_data)


@router.post("/test-multi-body-form-file", response=ResponseData, by_alias=True)
def test_multi_body_form_file(
    request,
    file: UploadedFile = File(...),
    i: int = Body(...),
    s: str = Form("a-str"),
    data: TestData4 = Body(...),
    nested_data: TestData = Form(..., alias="nested-data"),
):
    return dict(s=s, i=i, data=data, nested_data=nested_data)


@router.post("/test-multi-form-body-file", response=ResponseData, by_alias=True)
def test_multi_form_body_file(
    request,
    file: UploadedFile = File(...),
    i: int = Form(...),
    s: str = Body("a-str"),
    data: TestData4 = Form(...),
    nested_data: TestData = Body(..., alias="nested-data"),
):
    return dict(s=s, i=i, data=data, nested_data=nested_data)
