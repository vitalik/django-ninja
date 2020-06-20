from datetime import date


@api.get("/example")
def example(request, s: str = None, b: bool = None, d: date = None, i: int = None):
    return [s, b, d, i]
