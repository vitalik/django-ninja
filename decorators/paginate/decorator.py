import functools
from typing import Optional
from urllib import parse

from django.core.paginator import Page, Paginator
from django.utils.encoding import force_str


# based on https://github.com/vitalik/django-ninja/issues/104

def replace_query_param(url, key, val):
    (scheme, netloc, path, query, fragment) = parse.urlsplit(force_str(url))
    query_dict = parse.parse_qs(query, keep_blank_values=True)
    query_dict[force_str(key)] = [force_str(val)]
    query = parse.urlencode(sorted(query_dict.items()), doseq=True)
    return parse.urlunsplit((scheme, netloc, path, query, fragment))


def get_next_page_url(request, page: Page) -> Optional[str]:
    if not page.has_next():
        return None
    return replace_query_param(request.build_absolute_uri(), "page", page.number + 1)


def get_previous_page_url(request, page: Page) -> Optional[str]:
    if not page.has_previous():
        return None
    return replace_query_param(request.build_absolute_uri(), "page", page.number - 1)


def paginate(per_page=30):
    def paginate_decorator(func):
        per_page_value = per_page if isinstance(per_page, int) else 30

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            request = args[0]
            page = request.GET.get('page', 1)
            qs = func(*args, **kwargs)

            paginator_page = Paginator(qs, per_page=per_page_value).get_page(page)

            return {
                'count': paginator_page.paginator.count,
                'next': get_next_page_url(request, paginator_page),
                'previous': get_previous_page_url(request, paginator_page),
                'results': list(paginator_page.object_list)
            }

        return wrapper

    return paginate_decorator if isinstance(per_page, int) else paginate_decorator(per_page)
