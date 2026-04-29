from django.contrib import admin, messages
from django.db.models import F, Q
from django.db.models.functions import Collate
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils import timezone

from mesads.app.models import DemandeAccesLectureSeule


@admin.register(DemandeAccesLectureSeule)
class DemandeAccesLectureSeuleAdmin(admin.ModelAdmin):
    list_display = ("user", "administrator", "statut", "created_at")

    search_fields = ("user__email",)

    change_form_template = "admin/app/demande_gestion_prefecture/change_form.html"
    autocomplete_fields = ["user"]

    def response_change(self, request, obj):
        # Gestion du bouton "Valider"
        if "_valider" in request.POST:
            # TODO: Envoyer un mail de confirmation si on
            # passe on deploie la fonctionnalité au niveau national
            self.message_user(request, "Demande validée.", level=messages.SUCCESS)

            changelist_url = reverse(
                f"admin:{obj._meta.app_label}_{obj._meta.model_name}_changelist"
            )
            obj.statut = DemandeAccesLectureSeule.ACCEPTE
            obj.accepted_at = timezone.now().date()
            obj.save()
            return HttpResponseRedirect(changelist_url)

        elif "_refuser" in request.POST:
            self.message_user(request, "Demande refusée.", level=messages.ERROR)

            changelist_url = reverse(
                f"admin:{obj._meta.app_label}_{obj._meta.model_name}_changelist"
            )
            obj.statut = DemandeAccesLectureSeule.REFUSE
            obj.accepted_at = None
            obj.save()
            return HttpResponseRedirect(changelist_url)

        return super().response_change(request, obj)

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
