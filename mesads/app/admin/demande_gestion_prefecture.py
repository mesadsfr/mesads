from django.conf import settings
from django.contrib import admin, messages
from django.contrib.staticfiles import finders
from django.core.mail import EmailMultiAlternatives
from django.db.models import F, Q
from django.db.models.functions import Collate
from django.http import HttpResponseRedirect
from django.template.loader import render_to_string
from django.urls import reverse

from mesads.app.models import DemandeGestionPrefecture


@admin.register(DemandeGestionPrefecture)
class DemandeGestionPrefectureAdmin(admin.ModelAdmin):
    list_display = ("user", "administrator", "created_at")

    search_fields = ("user__email",)

    change_form_template = "admin/app/demande_gestion_prefecture/change_form.html"

    def response_change(self, request, obj):
        # Gestion du bouton "Valider"
        if "_valider" in request.POST:
            self.validation_demande(obj, request)
            self.message_user(request, "Demande validée.", level=messages.SUCCESS)

            changelist_url = reverse(
                f"admin:{obj._meta.app_label}_{obj._meta.model_name}_changelist"
            )
            obj.delete()
            return HttpResponseRedirect(changelist_url)

        return super().response_change(request, obj)

    def validation_demande(self, obj, request):
        obj.administrator.users.add(obj.user)
        email_subject = render_to_string(
            "demande_gestion_prefecture/email_demande_gestion_prefecture_result_subject.txt",
            {
                "demande": obj,
            },
            request=request,
        ).strip()
        email_content = render_to_string(
            "demande_gestion_prefecture/email_demande_gestion_prefecture_result_content.txt",
            {
                "request": request,
                "demande": obj,
                "email_contact": settings.MESADS_CONTACT_EMAIL,
            },
            request=request,
        )
        email_content_html = render_to_string(
            "demande_gestion_prefecture/email_demande_gestion_prefecture_result_content.mjml",
            {
                "request": request,
                "demande": obj,
                "email_contact": settings.MESADS_CONTACT_EMAIL,
            },
            request=request,
        )

        email = EmailMultiAlternatives(
            subject=email_subject,
            body=email_content,
            from_email=settings.MESADS_CONTACT_EMAIL,
            to=[obj.user.email],
        )
        email.attach_alternative(email_content_html, "text/html")

        file_path = finders.find("Guide d'utilisation.pdf")

        with open(file_path, "rb") as f:
            email.attach(
                "Guide d'utilisation.pdf",
                f.read(),
                "application/pdf",
            )

        email.send(fail_silently=True)

    def get_search_results(self, request, queryset, search_term):
        """The field Users.email uses a non-deterministic collation, which makes
        it impossible to perform a LIKE query on it.

        By overriding this method, we can specify the collation to use for the search.
        """
        use_distinct = True
        queryset = queryset.annotate(collated_email=Collate(F("user__email"), "C"))
        queryset = queryset.filter(
            Q(
                collated_email__icontains=search_term,
            )
            | Q(administrator__prefecture__libelle=search_term)
        )
        return (
            queryset,
            use_distinct,
        )
