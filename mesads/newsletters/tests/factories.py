import factory
from django.core.files.uploadedfile import SimpleUploadedFile

from ..models import NewsLetter


class NewsLetterFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = NewsLetter

    newsletter = factory.LazyFunction(
        lambda: SimpleUploadedFile(
            "test.pdf", b"%PDF-1.4 fake content", content_type="application/pdf"
        )
    )
