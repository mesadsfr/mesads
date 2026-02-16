from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import SuspiciousOperation
from django.core.mail import send_mail
from django.db.models import (
    BooleanField,
    Case,
    CharField,
    Count,
    DateTimeField,
    ExpressionWrapper,
    F,
    IntegerField,
    OuterRef,
    Q,
    Subquery,
    Value,
    When,
)
from django.db.models.functions import Cast, Coalesce, Now, Replace
from django.shortcuts import get_object_or_404, redirect
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.text import slugify
from django.views.generic import ListView, TemplateView, View
from reversion.views import RevisionMixin

from mesads.app.forms import SearchVehiculeForm
from mesads.fradm.models import EPCI, Aeroport, Commune, Prefecture
from mesads.utils_psql import SplitPart
from mesads.vehicules_relais.models import Vehicule

from ..models import (
    ADS,
    ADSManager,
    ADSManagerAdministrator,
    ADSManagerRequest,
    ADSUpdateLog,
)
from ..services import (
    get_ads_data_for_excel_export,
    get_gestionnaires_data_for_excel_export,
)
from .export import ExcelExporter


class ADSManagerAdministratorListeGestionnaires(ListView):
    template_name = "pages/ads_register/prefecture_liste_gestionnaires.html"
    model = ADSManager
    paginate_by = 50
    context_object_name = "ads_managers"
    ordering = ("content_type",)

    def get_queryset(self):
        latest_log_qs = ADSUpdateLog.objects.filter(ads=OuterRef("pk")).order_by(
            "-update_at"
        )

        # 2) Count how many ADS under this manager have latest_complete=True
        complete_updates_subquery_per_ads_manager = Subquery(
            ADS.objects.filter(ads_manager=OuterRef("id"))
            .annotate(
                latest_update_log=Subquery(latest_log_qs.values("update_at")[:1]),
                latest_update_log_is_complete=Subquery(
                    latest_log_qs.values("is_complete")[:1]
                ),
                latest_update_log_is_outdated=Case(
                    When(
                        latest_update_log__lt=ExpressionWrapper(
                            Now() - timedelta(days=ADSUpdateLog.OUTDATED_LOG_DAYS),
                            output_field=DateTimeField(),
                        ),
                        then=Value(True),
                    ),
                    default=Value(False),
                    output_field=BooleanField(),
                ),
            )
            .filter(
                latest_update_log_is_complete=True, latest_update_log_is_outdated=False
            )
            .values("ads_manager")
            .annotate(count=Count("pk"))
            .values("count")[:1],
            output_field=IntegerField(),
        )

        nb_ads_subq = Subquery(
            ADS.objects.filter(ads_manager=OuterRef("pk"))
            .values("ads_manager")
            .annotate(c=Count("pk"))
            .values("c")[:1],
            output_field=IntegerField(),
        )

        nb_requests_subq = Subquery(
            ADSManagerRequest.objects.filter(
                ads_manager=OuterRef("pk"),
                accepted=True,
            )
            .values("ads_manager")
            .annotate(c=Count("pk"))
            .values("c")[:1],
            output_field=IntegerField(),
        )

        qs = (
            ADSManager.objects.filter(
                administrator=self.kwargs["ads_manager_administrator"]
            )
            .annotate(
                nb_managers=Coalesce(
                    nb_requests_subq, Value(0), output_field=IntegerField()
                ),
                nb_ads=Coalesce(nb_ads_subq, Value(0), output_field=IntegerField()),
                complete_updates_count=Coalesce(
                    complete_updates_subquery_per_ads_manager,
                    Value(0),
                    output_field=IntegerField(),
                ),
                pourcentage_completion=Case(
                    When(
                        nb_ads__gt=0,
                        then=ExpressionWrapper(
                            F("complete_updates_count") / F("nb_ads") * 100,
                            output_field=IntegerField(),
                        ),
                    )
                ),
            )
            .order_by("content_type")
        )
        search = self.request.GET.get("search")

        if not search:
            return qs

        content_type_commune = ContentType.objects.get_for_model(Commune)
        content_type_prefecture = ContentType.objects.get_for_model(Prefecture)
        content_type_epci = ContentType.objects.get_for_model(EPCI)
        content_type_aeroport = ContentType.objects.get_for_model(Aeroport)

        communes_ids = Commune.objects.filter(libelle__icontains=search).values("pk")
        prefectures_ids = Prefecture.objects.filter(libelle__icontains=search).values(
            "pk"
        )
        epcis_ids = EPCI.objects.filter(name__icontains=search).values("pk")
        aeroport_ids = Aeroport.objects.filter(name__icontains=search).values("pk")

        qs = qs.filter(
            Q(content_type=content_type_commune, object_id__in=Subquery(communes_ids))
            | Q(
                content_type=content_type_prefecture,
                object_id__in=Subquery(prefectures_ids),
            )
            | Q(content_type=content_type_epci, object_id__in=Subquery(epcis_ids))
            | Q(
                content_type=content_type_aeroport, object_id__in=Subquery(aeroport_ids)
            )
        )
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # For each ADS, get its latest is_complete flag
        latest_log_qs = ADSUpdateLog.objects.filter(ads=OuterRef("pk")).order_by(
            "-update_at"
        )

        context["manager_ids"] = [
            request.ads_manager.id
            for request in ADSManagerRequest.objects.filter(user=self.request.user)
        ]

        nb_ads_completes_prefecture = (
            ADS.objects.filter(
                ads_manager__administrator=self.kwargs["ads_manager_administrator"],
            )
            .annotate(
                latest_update_log=Subquery(latest_log_qs.values("update_at")[:1]),
                latest_update_log_is_complete=Subquery(
                    latest_log_qs.values("is_complete")[:1]
                ),
                latest_update_log_is_outdated=Case(
                    When(
                        latest_update_log__lt=ExpressionWrapper(
                            Now() - timedelta(days=ADSUpdateLog.OUTDATED_LOG_DAYS),
                            output_field=DateTimeField(),
                        ),
                        then=Value(True),
                    ),
                    default=Value(False),
                    output_field=BooleanField(),
                ),
            )
            .filter(
                latest_update_log_is_complete=True, latest_update_log_is_outdated=False
            )
            .count()
        )

        nb_total_ads_prefecture = ADS.objects.filter(
            ads_manager__administrator=self.kwargs["ads_manager_administrator"]
        ).count()

        context["total_ads_for_prefecture"] = nb_total_ads_prefecture

        context["pourcentage_completion_prefecture"] = (
            round(nb_ads_completes_prefecture / nb_total_ads_prefecture * 100, 1)
            if nb_total_ads_prefecture
            else 0
        )

        context["nb_administrations"] = (
            ADSManager.objects
            .filter(administrator=self.kwargs["ads_manager_administrator"])
            .count()
        )

        context["search"] = self.request.GET.get("search")

        return context

    def post(self, request, *args, **kwargs):
        ads_manager = get_object_or_404(
            ADSManager, id=request.POST.get("ads_manager_id")
        )
        ADSManagerRequest.objects.create(
            user=self.request.user, ads_manager=ads_manager, accepted=True
        )
        messages.success(
            request,
            "Vous êtes bien devenu gestionnaire de cette administration",
        )
        return self.get(request, *args, **kwargs)


class ADSManagerAdminRequestsView(RevisionMixin, TemplateView):
    """This view is used by ADSManagerAdministrators to validate
    ADSManagerRequests and list changes made by ADSManagers."""

    template_name = "pages/ads_register/ads_manager_admin_requests.html"

    def get_context_data(self, **kwargs):
        """
        Populate context with the list of ADSManagerRequest current user can accept.
        """
        ctx = super().get_context_data(**kwargs)

        query = (
            ADSManagerRequest.objects.select_related(
                "ads_manager",
                "ads_manager__administrator",
                "user",
            )
            .prefetch_related(
                "ads_manager__content_type",
                "ads_manager__content_object",
            )
            .filter(ads_manager__administrator=self.kwargs["ads_manager_administrator"])
        )

        if self.request.GET.get("sort") == "name":
            ctx["sort"] = "name"
            ctx["ads_manager_requests"] = query.order_by(
                "ads_manager__administrator",
                "ads_manager__commune__libelle",
                "ads_manager__epci__name",
                "ads_manager__prefecture__libelle",
            )
        else:
            ctx["ads_manager_requests"] = query.order_by(
                "ads_manager__administrator",
                "-created_at",
            )
        return ctx

    def post(self, request, **kwargs):
        request_id = request.POST.get("request_id")
        action = request.POST.get("action")

        if action not in ("accept", "deny", "revoke", "authorize"):
            raise SuspiciousOperation("Invalid action")

        ads_manager_request = get_object_or_404(ADSManagerRequest, id=request_id)

        # Make sure current user can accept this request
        get_object_or_404(
            ADSManagerAdministrator,
            users__in=[request.user],
            adsmanager=ads_manager_request.ads_manager,
        )

        if action == "accept" or action == "authorize":
            ads_manager_request.accepted = True
        else:
            ads_manager_request.accepted = False
        ads_manager_request.save()

        # Send notification to user
        email_subject = render_to_string(
            "pages/email_ads_manager_request_result_subject.txt",
            {
                "ads_manager_request": ads_manager_request,
            },
            request=request,
        ).strip()
        email_content = render_to_string(
            "pages/email_ads_manager_request_result_content.txt",
            {
                "request": request,
                "ads_manager_request": ads_manager_request,
            },
            request=request,
        )
        email_content_html = render_to_string(
            "pages/email_ads_manager_request_result_content.mjml",
            {
                "request": request,
                "ads_manager_request": ads_manager_request,
            },
            request=request,
        )
        send_mail(
            email_subject,
            email_content,
            settings.MESADS_CONTACT_EMAIL,
            [ads_manager_request.user.email],
            fail_silently=True,
            html_message=email_content_html,
        )
        request_administrator = ads_manager_request.ads_manager.administrator
        return redirect(
            reverse(
                "app.ads-manager-admin.requests",
                kwargs={"prefecture_id": request_administrator.prefecture.id},
            )
        )


class ADSManagerExportView(ExcelExporter, View):
    ads_manager = None

    def setup(self, request, *args, **kwargs):
        self.ads_manager = get_object_or_404(ADSManager, id=kwargs.get("manager_id"))
        return super().setup(request, *args, **kwargs)

    def get_filename(self):
        administration = self.ads_manager.content_object.display_text()
        return slugify(f"ADS {administration}") + ".xlsx"

    def get_file_title(self):
        return f"ADS - {self.ads_manager.content_object.display_text().capitalize()}"

    def generate(self, workbook):
        headers, ads = get_ads_data_for_excel_export(ads_manager=self.ads_manager)

        self.add_sheet(
            workbook,
            "ADS enregistrées",
            "TableauADS",
            headers,
            ads,
        )


class PrefectureExportView(ExcelExporter, View):
    ads_manager_administrator = None

    def setup(self, request, *args, **kwargs):
        self.ads_manager_administrator = kwargs.get("ads_manager_administrator")
        return super().setup(request, *args, **kwargs)

    def get_filename(self):
        return f"ADS_prefecture_{self.ads_manager_administrator.prefecture.numero}.xlsx"

    def get_file_title(self):
        return (
            f"Informations des ADS et gestionnaires - "
            f"{self.ads_manager_administrator.prefecture.display_text().capitalize()}"
        )

    def generate(self, workbook):
        headers_ads, ads = get_ads_data_for_excel_export(
            ads_manager_administrator=self.ads_manager_administrator
        )

        self.add_sheet(
            workbook,
            "ADS enregistrées",
            "TableauADS",
            headers_ads,
            ads,
        )

        headers_managers, ads_managers = get_gestionnaires_data_for_excel_export(
            self.ads_manager_administrator
        )

        self.add_sheet(
            workbook,
            "Gestionnaires ADS",
            "TableauGestionnaires",
            headers_managers,
            ads_managers,
        )


class ADSManagerAdminUpdatesView(TemplateView):
    template_name = "pages/ads_register/ads_manager_admin_updates.html"

    def get_updates(self):
        query = """
            SELECT
                ads.id,
                ads.last_update,
                ads.number,
                adsmanager.id AS ads_manager_id,
                CASE
                    WHEN COUNT(revision.id) = 0 THEN NULL
                    ELSE COALESCE(JSON_AGG(JSON_BUILD_OBJECT(
                        'user_id', revision.user_id,
                        'user_email', "user".email,
                        'modification_date', revision.date_created
                    ) ORDER BY revision.date_created DESC), '[]'::json)
                END as updates,
                %(extra_fields)s
            FROM app_ads AS ads
            LEFT JOIN app_adsmanager AS adsmanager
                ON adsmanager.id = ads.ads_manager_id
            LEFT JOIN app_adsmanageradministrator AS adsmanageradministrator
                ON adsmanager.administrator_id = adsmanageradministrator.id
            LEFT JOIN reversion_version AS version
                ON (version.serialized_data::json -> 0 ->> 'model') = 'app.ads'
                AND (version.serialized_data::json -> 0 ->> 'pk')::bigint = ads.id
            LEFT JOIN reversion_revision AS revision
                ON version.revision_id = revision.id
            LEFT JOIN users_user AS "user"
                ON "user".id = revision.user_id
            WHERE
                adsmanageradministrator.id = %%s
            GROUP BY ads.id, adsmanager.id
            ORDER BY ads.last_update DESC
            LIMIT 100
        """ % {
            # The constructor of ADS retrieves the fields specified  in
            # SMART_VALIDATION_WATCHED_FIELDS. If we didn't explicitly select
            # them, the ORM would have to perform a lazy load for each object to
            # read them.
            "extra_fields": ", ".join(
                ['"%s"' % key for key in ADS.SMART_VALIDATION_WATCHED_FIELDS.keys()]
            )
        }
        ads_updated = list(
            ADS.objects.raw(
                query,
                (self.kwargs["ads_manager_administrator"].id,),
            )
        )

        ads_managers = {
            obj.id: obj
            for obj in ADSManager.objects.filter(
                id__in=[row.ads_manager_id for row in ads_updated]
            ).prefetch_related("content_type", "content_object")
        }

        return [
            {
                "ads": row,
                "ads_manager": ads_managers[row.ads_manager_id],
                "history_entries": row.updates,
            }
            for row in ads_updated
        ]

    def get_context_data(self, *args, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["updates"] = self.get_updates()
        return ctx


class RepertoireVehiculeRelaisView(ListView):
    template_name = "pages/ads_register/prefecture_vehicules_relais.html"
    paginate_by = 100

    def get_form(self):
        return SearchVehiculeForm(self.request.GET)

    def get_queryset(self):
        # .order_by("numero") doesn't work because with a string ordering,
        # 75-2 is higher than 75-100.
        # Instead we split the numero field and order by the first and second part.
        # Note the first part has to be cast to a string and not to an integer
        # because Corsica's departement number is 2A or 2B.
        qs = (
            Vehicule.objects.filter(
                departement__id=self.kwargs.get(
                    "ads_manager_administrator"
                ).prefecture.id
            )
            .annotate(
                part1=Cast(SplitPart("numero", Value("-"), Value(1)), CharField()),
                part2=Cast(SplitPart("numero", Value("-"), Value(2)), IntegerField()),
                immatriculation_clean=Replace(
                    F("immatriculation"), Value("-"), Value("")
                ),
            )
            .order_by("part1", "part2")
            .select_related("proprietaire")
        )

        form = self.get_form()
        if form.is_valid():
            immatriculation = form.cleaned_data["immatriculation"]
            if immatriculation:
                qs = qs.filter(
                    immatriculation_clean__icontains=immatriculation.replace("-", "")
                )
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = self.get_form()

        context["form"] = form
        context["ads_manager_administrator"] = self.kwargs.get(
            "ads_manager_administrator"
        )

        return context


class VehiculeView(TemplateView):
    template_name = "pages/ads_register/prefecture_vehicule_relais_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["vehicule"] = get_object_or_404(Vehicule, numero=kwargs["numero"])
        context["ads_manager_administrator"] = self.kwargs.get(
            "ads_manager_administrator"
        )
        return context
