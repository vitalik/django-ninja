from http import HTTPStatus

import django
import pytest
from django.test import Client, modify_settings
from django.urls import reverse

from ninja import NinjaAPI, Router
from ninja.errors import ConfigError


@pytest.mark.skipif(django.VERSION < (3, 2), reason="requires django 3.2 or higher")
def test_can_register_routes_in_apps_ready(client: Client):
    url = reverse("late-registration:registered-late")
    response = client.get(url)
    assert response.status_code == HTTPStatus.OK

    with modify_settings(INSTALLED_APPS={"remove": ["someapp"]}):
        # "Uninstalling" an app to trigger apps.ready to run a second time
        response = client.get(url)
        assert response.status_code == HTTPStatus.OK


def test_build_routers_raises_config_error_if_attached_to_an_api():
    router = Router()
    NinjaAPI().add_router("/path", router)

    match = r"Router@'/some/prefix' has already been attached to API NinjaAPI:1.0.0"
    with pytest.raises(ConfigError, match=match):
        router.build_routers("/some/prefix")
