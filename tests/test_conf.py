from ninja.conf import settings


def test_default_configuration():
    assert settings.PAGINATION_CLASS == "ninja.pagination.LimitOffsetPagination"
    assert settings.PAGINATION_PER_PAGE == 100
