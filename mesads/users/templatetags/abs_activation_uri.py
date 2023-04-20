from django import template
from django.urls import reverse


register = template.Library()


@register.simple_tag(takes_context=True)
def abs_activation_uri(context, activation_key):
    request = context["request"]
    rel = reverse(
        "django_registration_activate", kwargs={"activation_key": activation_key}
    )
    return request.build_absolute_uri(rel)
