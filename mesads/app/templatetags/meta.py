from django import template

register = template.Library()


@register.filter
def meta(obj, field):
    """Returns the _meta attribute of an object. This is useful because django
    doesn't allow to access fields starting with an underscore in templates."""
    return getattr(obj._meta, field)
