from django.contrib import admin
from django.urls import path
from late_router_registration.routers import api_late_registration

from ninja import NinjaAPI

api_v1 = NinjaAPI()
api_v1.add_router("events", "someapp.api.router")
# TODO: check ^ for possible mistakes like `/events` `events/``


api_v2 = NinjaAPI(version="2.0.0")


@api_v2.get("events")
def newevents2(request):
    return "events are gone"


api_v3 = NinjaAPI(version="3.0.0")


@api_v3.get("events")
def newevents3(request):
    return "events are gone 3"


@api_v3.get("foobar")
def foobar(request):
    return "foobar"


@api_v3.post("foobar")
def post_foobar(request):
    return "foobar"


@api_v3.put("foobar", url_name="foobar_put")
def put_foobar(request):
    return "foobar"


api_multi_param = NinjaAPI(version="1.0.1")
api_multi_param.add_router("", "multi_param.api.router")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", api_v1.urls),
    path("api/v2/", api_v2.urls),
    path("api/v3/", api_v3.urls),
    path("api/mp/", api_multi_param.urls),
    path("api/late-registration", api_late_registration.urls),
]
