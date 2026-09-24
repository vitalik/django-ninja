from django.urls import path

from ninja import NinjaAPI

api = NinjaAPI(urls_namespace="late-urls")


@api.get("/initial", url_name="initial")
def initial(request):
    return {"ok": True}


urlpatterns = [path("late/", api.urls)]
