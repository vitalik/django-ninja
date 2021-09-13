import copy

from django.urls import path

from ninja import NinjaAPI

from .api import router

api_multi_param = NinjaAPI(version="1.0.1")
router = copy.deepcopy(router)
router.api = None
api_multi_param.add_router("", router)

urlpatterns = [
    path("api/", api_multi_param.urls),
]
