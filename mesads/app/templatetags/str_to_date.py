from datetime import datetime

from django import template


register = template.Library()


@register.filter
def str_to_date(value, format="%Y-%m-%d"):
    """Convert the string "value" to a Date object, if possible. If not, return
    the original value.

    This is useful for forms with a date input. When the form is valid, the date
    field is converted to a Date object, but if the form is invalid, the date
    field is a string.
    """
    try:
        return datetime.strptime(value, format).date()
    except (TypeError, ValueError):  # TypeError if value is already a date, ValueError if wrong format
        return value
