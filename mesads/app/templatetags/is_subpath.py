from django import template

register = template.Library()


@register.simple_tag
def is_subpath(first, second, num=1):
    """Given two URLs, returns true if the first and the second are similar up to the given number of subpaths.

    Examples:

    >>> is_subpath("/menu/subpage/xxx", "/menu/subpage/yyy", 1)
    True
    >>> is_subpath("/menu/subpage/xxx", "/menu/subpage/yyy", 2)
    True
    >>> is_subpath("/menu/subpage/xxx", "/menu/subpage/yyy", 3)
    False
    """
    assert num > 0
    first_parts = first.split("/")
    second_parts = second.split("/")
    return first_parts[: num + 1] == second_parts[: num + 1]
