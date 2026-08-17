from django.test import override_settings

from ninja.conf import settings


def test_default_configuration():
    assert settings.PAGINATION_CLASS == "ninja.pagination.LimitOffsetPagination"
    assert settings.PAGINATION_PER_PAGE == 100


def test_override_settings_updates_ninja_settings():
    assert settings.NUM_PROXIES is None
    assert settings.PAGINATION_PER_PAGE == 100

    with override_settings(NINJA_NUM_PROXIES=3, NINJA_PAGINATION_PER_PAGE=20):
        assert settings.NUM_PROXIES == 3
        assert settings.PAGINATION_PER_PAGE == 20

    assert settings.NUM_PROXIES is None
    assert settings.PAGINATION_PER_PAGE == 100
