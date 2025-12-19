from dataclasses import dataclass

from django import template

register = template.Library()


@dataclass
class Page:
    is_first: bool = False
    is_prev: bool = False
    is_current: bool = False
    is_ellipsis: bool = False
    is_next: bool = False
    is_last: bool = False
    number: int = None


@register.inclusion_tag("pagination_links.html", takes_context=True)
def show_pagination_links(context, page_obj):
    """Links to render pagination.

    The output is as follow, for a table of 11 pages when the current page is
    5:

      |< < … 4 5 6 … 11 > >|

    where:

    - |< and < are only displayed if there is a previous page
    - the first ellipsis is only displayed if we are on a page higher than 2
    - 4 is the previous page number, only displayed if we are not on the first
      page
    - 5 has the flag "is_current" to true
    - 6 is the next page number, only displayed if there is one
    - the second ellipsis is only displayed if we are not on the page just
      before the last one
    - links to next pages > and >| are only displayed if necessary
    """
    if not page_obj.has_other_pages():
        return {}

    pages = []

    # Links to first page and previous page only if there is a previous page.
    if page_obj.has_previous():
        pages.append(Page(is_first=True, number=1))
        pages.append(Page(is_prev=True, number=page_obj.previous_page_number))

    # Add ellipsis
    if page_obj.number > 2:
        pages.append(Page(is_ellipsis=True))

    if page_obj.has_previous():
        pages.append(Page(number=page_obj.number - 1))

    pages.append(Page(is_current=True, number=page_obj.number))

    if page_obj.has_next():
        pages.append(Page(number=page_obj.number + 1))

    if page_obj.number < page_obj.paginator.num_pages - 2:
        pages.append(Page(is_ellipsis=True))

    if page_obj.number < page_obj.paginator.num_pages - 1:
        pages.append(Page(number=page_obj.paginator.num_pages))

    if page_obj.has_next():
        pages.append(Page(is_next=True, number=page_obj.next_page_number))
        pages.append(Page(is_last=True, number=page_obj.paginator.num_pages))

    request = context["request"]
    extra_qs = "&".join(
        [f"{key}={value}" for key, value in request.GET.items() if key != "page"]
    )

    return {
        "pages": pages,
        "extra_qs": extra_qs,
    }
