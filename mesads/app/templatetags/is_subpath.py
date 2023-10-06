from django import template

register = template.Library()


@register.simple_tag
def is_subpath(first, second, num=2):
    """Given two URLs, returns true if the first and the second are similar up to the given number of subpaths."""
    first_parts = first.split("/")
    second_parts = second.split("/")
    return first_parts[:num] == second_parts[:num]
