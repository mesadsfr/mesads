from django import template
from django.utils.safestring import mark_safe
from markdownx.utils import markdownify as utils_markdownify

register = template.Library()


@register.filter
def markdownify(text):
    return mark_safe(utils_markdownify(text))
