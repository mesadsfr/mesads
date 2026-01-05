from django import template

register = template.Library()


@register.filter
def selectattr(items, name):
    """Equivalent of the Jinja2 filter selectattr."""
    return [getattr(item, name) for item in items]
