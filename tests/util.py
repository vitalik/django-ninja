import pydantic


def pydantic_ref_fix(data: dict):
    "In pydantic 1.7 $ref was changed to allOf: [{'$ref': ...}] but in 2.9 it was changed back"
    v = tuple(map(int, pydantic.version.version_short().split(".")))
    if v < (1, 7) or v >= (2, 9):
        return data

    result = data.copy()
    if "$ref" in data:
        result["allOf"] = [{"$ref": result.pop("$ref")}]
    return result
