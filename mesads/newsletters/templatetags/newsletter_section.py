from django import template

from mesads.newsletters.models import NewsLetter

register = template.Library()


@register.inclusion_tag("pages/accueil/accueil_newsletters.html")
def accueil_newsletters():
    newsletters = NewsLetter.objects.order_by("-newsletter_date")

    derniere_newsletter = newsletters.first()

    return {
        "derniere_newsletter": derniere_newsletter,
        "trois_dernieres_newsletters": list(newsletters[1:4]) if newsletters else [],
    }
