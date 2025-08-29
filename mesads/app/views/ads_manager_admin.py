from django.conf import settings
from django.core.exceptions import SuspiciousOperation
from django.db.models import (
    OuterRef,
    Subquery,
    Count,
    IntegerField,
    BooleanField,
    Value,
    CharField,
    F,
)
from django.db.models.functions import Cast, Replace
from django.core.mail import send_mail
from django.shortcuts import get_object_or_404, redirect
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.text import slugify
from django.views.generic import RedirectView, View, TemplateView, ListView

from reversion.views import RevisionMixin

from ..models import (
    ADS,
    ADSManagerAdministrator,
    ADSManagerRequest,
    ADSManager,
    ADSUpdateLog,
)
from mesads.app.forms import SearchVehiculeForm
from mesads.vehicules_relais.models import Vehicule, Proprietaire
from mesads.utils_psql import SplitPart

from .export import ADSExporter


class ADSManagerAdminIndexView(RedirectView):
    def get_redirect_url(self, *args, **kwargs):
        administrators = ADSManagerAdministrator.objects.filter(
            users__in=[self.request.user]
        )
        if len(administrators):
            return reverse(
                "app.ads-manager-admin.details",
                kwargs={"prefecture_id": administrators[0].prefecture.id},
            )
        return reverse("app.ads-manager.index")


class ADSManagerAdminDetailsView(RevisionMixin, TemplateView):

    template_name = "pages/ads_register/ads_manager_admin.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        pending_requests = ADSManagerRequest.objects.filter(
            ads_manager__administrator=self.kwargs["ads_manager_administrator"]
        ).filter(accepted__isnull=True)
        ctx["pending_requests_count"] = pending_requests.count()
        return ctx


class ADSManagerAdministratorView(TemplateView):
    template_name = "pages/ads_register/espace_prefecture_gestionnaires.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # All ADS for the manager
        ads_count_subquery = (
            ADS.objects.filter(
                ads_manager=OuterRef("ads_manager_id"),
                deleted_at__isnull=True,
            )
            .values("ads_manager")
            .annotate(count=Count("*"))
            .values("count")[:1]
        )

        # For each ADS, get its latest is_complete flag
        latest_complete = Subquery(
            ADSUpdateLog.objects.filter(ads=OuterRef("pk"))
            .order_by("-update_at")
            .values("is_complete")[:1],
            output_field=BooleanField(),
        )

        # 2) Count how many ADS under this manager have latest_complete=True
        complete_updates_subquery_per_ads_manager = Subquery(
            ADS.objects.filter(ads_manager=OuterRef("ads_manager_id"))
            .annotate(latest_complete=latest_complete)
            .filter(latest_complete=True)
            .values("ads_manager")
            .annotate(count=Count("pk"))
            .values("count")[:1],
            output_field=IntegerField(),
        )

        complete_ads_per_admin_per_ads_manager_administrator = Subquery(
            ADS.objects.filter(
                ads_manager__administrator=OuterRef("pk"),
                deleted_at__isnull=True,
            )
            .annotate(latest_complete=latest_complete)
            .filter(latest_complete=True)
            .values("ads_manager__administrator")
            .annotate(count=Count("pk"))
            .values("count")[:1],
            output_field=IntegerField(),
        )

        context["user_ads_manager_requests"] = ADSManagerRequest.objects.filter(
            user=self.request.user
        ).annotate(
            ads_count=Subquery(ads_count_subquery, output_field=IntegerField()),
            complete_updates_count=Subquery(
                complete_updates_subquery_per_ads_manager, output_field=IntegerField()
            ),
        )

        total_ads_per_ads_manager_admininistrator = Subquery(
            ADS.objects.filter(
                ads_manager__administrator=OuterRef("pk"),
                deleted_at__isnull=True,
            )
            .values("ads_manager__administrator")
            .annotate(count=Count("pk"))
            .values("count")[:1],
            output_field=IntegerField(),
        )

        context["ads_managers_administrator"] = (
            ADSManagerAdministrator.objects.select_related("prefecture")
            .filter(id=self.kwargs["ads_manager_administrator"].id)
            .annotate(
                ads_count=total_ads_per_ads_manager_admininistrator,
                complete_ads_count=complete_ads_per_admin_per_ads_manager_administrator,
            )
            .first()
        )

        return context


class ADSManagerAdminRequestsView(RevisionMixin, TemplateView):
    """This view is used by ADSManagerAdministrators to validate
    ADSManagerRequests and list changes made by ADSManagers."""

    template_name = "pages/ads_register/ads_manager_admin_requests.html"

    def get_context_data(self, **kwargs):
        """Populate context with the list of ADSManagerRequest current user can accept."""
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

        if action not in ("accept", "deny"):
            raise SuspiciousOperation("Invalid action")

        ads_manager_request = get_object_or_404(ADSManagerRequest, id=request_id)

        # Make sure current user can accept this request
        get_object_or_404(
            ADSManagerAdministrator,
            users__in=[request.user],
            adsmanager=ads_manager_request.ads_manager,
        )

        if action == "accept":
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
        return redirect(
            reverse(
                "app.ads-manager-admin.requests",
                kwargs={
                    "prefecture_id": ads_manager_request.ads_manager.administrator.prefecture.id
                },
            )
        )


class ADSManagerExportView(View, ADSExporter):
    def get(self, request, manager_id):
        self.ads_manager = get_object_or_404(ADSManager, id=manager_id)
        return self.generate()

    def get_filename(self):
        administration = self.ads_manager.content_object.display_text()
        return slugify(f"ADS {administration}") + ".xlsx"

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(ads_manager=self.ads_manager)


class PrefectureExportView(View, ADSExporter):
    def get(self, request, ads_manager_administrator):
        self.ads_manager_administrator = ads_manager_administrator
        return self.generate()

    def get_filename(self):
        return f"ADS_prefecture_{self.ads_manager_administrator.prefecture.numero}.xlsx"

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(ads_manager__administrator=self.ads_manager_administrator)

    def add_sheets(self, workbook):
        super().add_sheets(workbook)
        sheet = workbook.add_worksheet("Gestionnaires ADS")
        sheet.write_row(
            0,
            0,
            (
                "Nom de l'administration",
                "Nombre d'ADS",
                "Statut de la gestion des ADS",
                "Arrêté délimitant le nombre d'ADS",
            ),
        )
        # Applying bold format to headers
        bold_format = workbook.add_format({"bold": True})
        sheet.set_row(0, None, bold_format)

        for idx, ads_manager in enumerate(
            self.ads_manager_administrator.ordered_adsmanager_set()
        ):
            status = ""
            if ads_manager.no_ads_declared:
                status = "L'administration a déclaré ne gérer aucune ADS"
            elif ads_manager.epci_delegate:
                status = (
                    "La gestion des ADS est déléguée à %s"
                    % ads_manager.epci_delegate.display_fulltext()
                )

            decrees_count = ads_manager.adsmanagerdecree_set.count()

            sheet.write_row(
                idx + 1,
                0,
                (
                    ads_manager.content_object.display_text(),
                    ads_manager.ads_set.count() or "",
                    status,
                    (
                        f"{decrees_count} document(s) enregistré(s)"
                        if decrees_count
                        else ""
                    ),
                ),
            )
        sheet.autofit()


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
        # .order_by("numero") doesn't work because with a string ordering, 75-2 is higher than 75-100.
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
