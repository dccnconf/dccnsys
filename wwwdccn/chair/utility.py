import math

from django.http import Http404
from django.urls import reverse


ITEMS_PER_PAGE = 10


def validate_chair_access(user, conference):
    if user not in conference.chairs.all():
        raise Http404


def build_paged_view_context(request, items, page, viewname, kwargs):
    num_items = len(items)
    num_pages = int(math.ceil(num_items / ITEMS_PER_PAGE))

    if page < 1 or page > max(num_pages, 1):
        raise Http404

    first_index = min((page - 1) * ITEMS_PER_PAGE, num_items)
    last_index = min(page * ITEMS_PER_PAGE, num_items)
    first_page_url, last_page_url = '', ''
    prev_page_url, next_page_url = '', ''
    query_string = request.GET.urlencode()

    def _append_query_string(url):
        return url + '?' + query_string if query_string and url else url

    if page > 1:
        prev_page_url = reverse(
            viewname, kwargs=dict(kwargs, **{'page': page-1}))
        first_page_url = reverse(
            viewname, kwargs=dict(kwargs, **{'page': 1}))

    if page < num_pages:
        next_page_url = reverse(
            viewname, kwargs=dict(kwargs, **{'page': page+1}))
        last_page_url = reverse(
            viewname, kwargs=dict(kwargs, **{'page': num_pages}))

    page_urls = []
    for pi in range(1, num_pages + 1):
        page_urls.append(
            _append_query_string(
                reverse(viewname, kwargs=dict(kwargs, **{'page': pi}))
            )
        )

    return {
        'items': items[first_index:last_index],
        'num_items': num_items,
        'num_pages': num_pages,
        'curr_page': page,
        'prev_page_url': _append_query_string(prev_page_url),
        'next_page_url': _append_query_string(next_page_url),
        'first_page_url': _append_query_string(first_page_url),
        'last_page_url': _append_query_string(last_page_url),
        'page_urls': page_urls,
        'first_index': first_index + 1,
        'last_index': last_index,
    }
