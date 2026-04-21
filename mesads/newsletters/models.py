from django.db import models


class NewsLetter(models.Model):
    newsletter_date = models.DateField(verbose_name="Date d'envoi")

    newsletter = models.FileField(
        verbose_name="Newsletter (format PDF)", upload_to="newsletters/"
    )

    class Meta:
        verbose_name = "Newsletter"
        verbose_name_plural = "Newsletters"

    def __str__(self):
        return f"Newsletter du {self.newsletter_date.strftime('%d/%m/%Y')}"
