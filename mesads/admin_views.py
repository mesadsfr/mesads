import calendar
from datetime import date, timedelta

from django.db.models import Q, OuterRef, Subquery, BooleanField
from django.views.generic import TemplateView
from django.utils import timezone

from mesads.app.models import ADS, ADSUpdateLog
from mesads.users.models import UserAuditEntry


class StatistiquesView(TemplateView):
    template_name = "admin/statistiques.html"

    def get_pourcentage_ads_valide(self) -> float:
        date_limite_completion = timezone.now() - timedelta(
            days=ADSUpdateLog.OUTDATED_LOG_DAYS
        )
        ads_count = ADS.objects.count()
        last_log_valid = (
            ADSUpdateLog.objects.filter(
                ads=OuterRef("pk"), update_at__gte=date_limite_completion
            )
            .order_by("-update_at")
            .values("is_complete")[:1]
        )

        ads_complete_count = (
            ADS.objects.annotate(
                last_log_valid=Subquery(last_log_valid, output_field=BooleanField())
            )
            .filter(last_log_valid=True)
            .count()
        )

        return round((ads_complete_count / ads_count) * 100, 2) if ads_count != 0 else 0

    def get_nombre_creation_modification_ads(
        self, start_date: date, end_date: date
    ) -> int:
        return ADS.objects.filter(
            Q(creation_date__gte=start_date, creation_date__lte=end_date)
            | Q(last_update__gte=start_date, last_update__lte=end_date)
        ).count()

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
        return context
