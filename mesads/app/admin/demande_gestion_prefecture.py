from django.conf import settings
from django.contrib import admin
from django.contrib.staticfiles import finders
from django.core.mail import EmailMultiAlternatives
from django.db.models import F, Q
from django.db.models.functions import Collate
from django.template.loader import render_to_string
from django.utils import timezone

from mesads.app.models import ADSManagerAdministrator, DemandeGestionPrefecture


class AdministratorSelectFilter(admin.SimpleListFilter):
    title = "Prefecture"
    parameter_name = "prefecture"

    def lookups(self, request, model_admin):
        return [
            (administrator.pk, administrator.prefecture)
            for administrator in ADSManagerAdministrator.objects.order_by(
                "prefecture__numero"
            )
        ]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(administrator=self.value())
        return queryset


@admin.register(DemandeGestionPrefecture)
class DemandeGestionPrefectureAdmin(admin.ModelAdmin):
    autocomplete_fields = ["user"]
    list_display = ("user", "prefecture", "statut", "created_at")

    search_fields = ("user__email",)

    list_filter = ("statut", AdministratorSelectFilter)

    @admin.display(description="Préfecture")
    def prefecture(self, obj):
        return obj.administrator.prefecture

    def save_model(self, request, obj, form, change):
        accepted = False
        if obj.pk and change:
            old_obj = self.model.objects.get(pk=obj.pk)
            if (
                old_obj.statut != DemandeGestionPrefecture.ACCEPTE
                and obj.statut == DemandeGestionPrefecture.ACCEPTE
            ):
                obj.accepted_at = timezone.now()
                accepted = True

        super().save_model(request, obj, form, change)

        if accepted:
            self.validation_demande(obj, request)

    def validation_demande(self, obj, request):
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

        file_path = finders.find("Guide d'utilisation Préfectures.pdf")

        with open(file_path, "rb") as f:
            email.attach(
                "Guide d'utilisation Préfectures.pdf",
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
