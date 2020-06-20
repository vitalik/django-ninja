from ninja.security import HttpBasicAuth


class BasicAuth(HttpBasicAuth):
    def authenticate(self, request, username, password):
        if username == "admin" and password == "secret":
            return username


@api.get("/basic", auth=BasicAuth())
def basic(request):
    return {"httpuser": request.auth}
