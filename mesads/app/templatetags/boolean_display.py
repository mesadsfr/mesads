from django import template

register = template.Library()


@register.filter
def boolean_display(value):
    if value is None:
        return "Inconnu"
    elif value:
        return "Oui"
    else:
        return "Non"
