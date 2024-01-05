import pkg_resources

import yaml

from django import template
from django.urls import resolve
from django.utils.html import escape
from django.template import Template
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag(takes_context=True)
def html_metadata(context):
    """Return the HTML title and meta description."""
    data = pkg_resources.resource_string(__name__, "../../html_metadata.yml")
    metadata = yaml.safe_load(data)
    request = context["request"]
    url_name = resolve(request.path_info).url_name

    metadata_title = metadata.get("urls", {}).get(url_name, {}).get("title")
    metadata_description = metadata.get("urls", {}).get(url_name, {}).get("description")

    title = Template(metadata_title).render(context)
    description = Template(metadata_description).render(context)

    ret = ""
    if metadata_title:
        ret += f"<title>{escape(title)}</title>\n"
    if metadata_description:
        ret += f'<meta name="description" content="{escape(description)}">\n'
    return mark_safe(ret)
