import calendar
from datetime import date, timedelta

from django.db.models import BooleanField, Count, OuterRef, Q, Subquery, Sum
from django.utils import timezone
from django.views.generic import TemplateView

from mesads.app.models import ADS, ADSUpdateLog, InscriptionListeAttente
from mesads.users.models import NoteUtilisateur, UserAuditEntry

PREFECTURE_TEST = "999"


class StatistiquesView(TemplateView):
    template_name = "admin/statistiques.html"

    def get_pourcentage_ads_valide(self) -> float:
        date_limite_completion = timezone.now() - timedelta(
            days=ADSUpdateLog.OUTDATED_LOG_DAYS
        )
        ads_qs = ADS.objects.exclude(
            ads_manager__administrator__prefecture__numero=PREFECTURE_TEST
        )
        ads_count = ads_qs.count()
        last_log_valid = (
            ADSUpdateLog.objects.filter(
                ads=OuterRef("pk"), update_at__gte=date_limite_completion
            )
            .order_by("-update_at")
            .values("is_complete")[:1]
        )

        ads_complete_count = (
            ads_qs.annotate(
                last_log_valid=Subquery(last_log_valid, output_field=BooleanField())
            )
            .filter(last_log_valid=True)
            .count()
        )

        return round((ads_complete_count / ads_count) * 100, 2) if ads_count != 0 else 0

    def get_nombre_creation_modification_ads(
        self, start_date: date, end_date: date
    ) -> int:
        return (
            ADS.objects.filter(
                Q(creation_date__gte=start_date, creation_date__lte=end_date)
                | Q(last_update__gte=start_date, last_update__lte=end_date)
            )
            .exclude(ads_manager__administrator__prefecture__numero=PREFECTURE_TEST)
            .count()
        )

    def get_nombre_connexions_unique(self, start_date: date, end_date: date) -> int:
        return (
            UserAuditEntry.objects.filter(
                created_at__gte=start_date,
                created_at__lte=end_date,
                action="login",
            )
            .distinct("user")
            .count()
        )

    def get_nombre_creation_liste_attente(
        self, start_date: date, end_date: date
    ) -> int:
        return (
            InscriptionListeAttente.objects.filter(
                date_creation__date__gte=start_date, date_creation__date__lt=end_date
            )
            .exclude(ads_manager__administrator__prefecture__numero=PREFECTURE_TEST)
            .count()
        )

    def get_nombre_ads_cree_via_liste_attente(
        self, start_date: date, end_date: date
    ) -> int:
        return (
            InscriptionListeAttente.with_deleted.filter(
                deleted_at__isnull=False,
                deleted_at__date__gte=start_date,
                deleted_at__date__lt=end_date,
                motif_archivage=InscriptionListeAttente.ADS_ATTRIBUEE,
            )
            .exclude(ads_manager__administrator__prefecture__numero=PREFECTURE_TEST)
            .count()
        )

    def get_note_moyenne_qualite(self) -> tuple[float, int]:
        notes = NoteUtilisateur.objects.filter(note_qualite__isnull=False)
        total_notes = notes.aggregate(total=Sum("note_qualite"))["total"]
        count = notes.count()
        if count == 0:
            return 0, 0

        else:
            return round(total_notes / count, 2), count

    def get_note_moyenne_facilite(self) -> tuple[float, int]:
        notes = NoteUtilisateur.objects.filter(note_facilite__isnull=False)
        total_notes = notes.aggregate(total=Sum("note_facilite"))["total"]
        count = notes.count()
        if count == 0:
            return 0, 0

        else:
            return round(total_notes / count, 2), count

    def get_note_qualite_repartition(self):
        notes = (
            NoteUtilisateur.objects.filter(note_qualite__isnull=False)
            .values("note_qualite")
            .annotate(nb=Count("id"))
        )
        counts = {item["note_qualite"]: item["nb"] for item in notes}

        repartition = [{"note": n, "nb": counts.get(n, 0)} for n in range(1, 6)]

        return repartition

    def get_note_facilite_repartition(self):
        notes = (
            NoteUtilisateur.objects.filter(note_facilite__isnull=False)
            .values("note_facilite")
            .annotate(nb=Count("id"))
        )
        counts = {item["note_facilite"]: item["nb"] for item in notes}

        repartition = [{"note": n, "nb": counts.get(n, 0)} for n in range(1, 6)]

        return repartition

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        if self.request.GET.get("start_date") and self.request.GET.get("end_date"):
            context["start_date"] = self.request.GET.get("start_date")
            context["end_date"] = self.request.GET.get("end_date")
        else:
            today = date.today()
            context["start_date"] = date(today.year, today.month, 1)
            nb_jours = calendar.monthrange(today.year, today.month)[1]
            context["end_date"] = date(today.year, today.month, nb_jours)

        context["nombre_connexions"] = self.get_nombre_connexions_unique(
            context["start_date"], context["end_date"]
        )
        context["nombre_creation_modification_ads"] = (
            self.get_nombre_creation_modification_ads(
                context["start_date"], context["end_date"]
            )
        )
        context["pourcentage_ads_valide_et_complete"] = (
            self.get_pourcentage_ads_valide()
        )

        context["nombre_inscriptions_creees"] = self.get_nombre_creation_liste_attente(
            context["start_date"], context["end_date"]
        )
        context["nombre_ads_liste_attente"] = (
            self.get_nombre_ads_cree_via_liste_attente(
                context["start_date"], context["end_date"]
            )
        )

        context["note_qualite_repartition"] = self.get_note_qualite_repartition()
        context["note_facilite_repartition"] = self.get_note_facilite_repartition()

        avg_note_facilite, count_note_facilite = self.get_note_moyenne_facilite()
        avg_note_qualite, count_note_qualite = self.get_note_moyenne_qualite()
        context["avg_note_facilite"] = avg_note_facilite
        context["count_note_facilite"] = count_note_facilite
        context["avg_note_qualite"] = avg_note_qualite
        context["count_note_qualite"] = count_note_qualite
        return context
