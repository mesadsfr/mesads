from datetime import date, timedelta

import pytest

from ..templatetags.newsletter_section import accueil_newsletters
from .factories import NewsLetterFactory

pytestmark = pytest.mark.django_db


def test_accueil_newsletter_empty():
    context = accueil_newsletters()

    assert context.get("derniere_newsletter") is None
    assert context.get("trois_dernieres_newsletters") == []


def test_accueil_newxsletter_with_one():
    newsletter = NewsLetterFactory(newsletter_date=date.today())
    context = accueil_newsletters()

    assert context.get("derniere_newsletter") == newsletter
    assert context.get("trois_dernieres_newsletters") == []


def test_accueil_newxsletter_with_three():
    newsletter_1 = NewsLetterFactory(newsletter_date=date.today())
    newsletter_2 = NewsLetterFactory(newsletter_date=date.today() - timedelta(days=1))
    newsletter_3 = NewsLetterFactory(newsletter_date=date.today() - timedelta(days=2))
    context = accueil_newsletters()

    assert context.get("derniere_newsletter") == newsletter_1
    assert context.get("trois_dernieres_newsletters") == [newsletter_2, newsletter_3]


def test_accueil_newxsletter_with_five():
    newsletter_1 = NewsLetterFactory(newsletter_date=date.today())
    newsletter_2 = NewsLetterFactory(newsletter_date=date.today() - timedelta(days=1))
    newsletter_3 = NewsLetterFactory(newsletter_date=date.today() - timedelta(days=2))
    newsletter_4 = NewsLetterFactory(newsletter_date=date.today() - timedelta(days=3))
    NewsLetterFactory(newsletter_date=date.today() - timedelta(days=4))
    context = accueil_newsletters()

    assert context.get("derniere_newsletter") == newsletter_1
    assert context.get("trois_dernieres_newsletters") == [
        newsletter_2,
        newsletter_3,
        newsletter_4,
    ]
