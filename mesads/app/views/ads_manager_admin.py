from django.conf import settings
from django.core.exceptions import SuspiciousOperation
from django.core.mail import send_mail
from django.db import connection
from django.shortcuts import get_object_or_404, redirect
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.text import slugify
from django.views.generic import RedirectView, View, TemplateView

from reversion.views import RevisionMixin

from ..models import (
    ADS,
    ADSManagerAdministrator,
    ADSManagerRequest,
    ADSManager,
)

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
    """This view is used by ADSManagerAdministrators to validate
    ADSManagerRequests and list changes made by ADSManagers."""

    template_name = "pages/ads_register/ads_manager_admin.html"

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
                "app.ads-manager-admin.details",
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

            sheet.write_row(
                idx + 1,
                0,
                (
                    ads_manager.content_object.display_text(),
                    ads_manager.ads_set.count() or "",
                    status,
                ),
            )
        sheet.autofit()


class ADSManagerAdminUpdatesView(TemplateView):
    template_name = "pages/ads_register/ads_manager_admin_updates.html"

    def get_updates(self, cursor):
        # You might be wondering why we didn't implement pagination and why we
        # limit to 100 results.
        # Long story short, it's because we are using a raw query and pagination
        # needs to be handled manually, and I've spent way too much time on this
        # already.
        # Alternatively we could use the django ORM instead of a raw query, but
        # good luck with that.
        cursor.execute(
            """
            SELECT
                ads.id AS id,
                adsmanager.id,
                CASE
                    WHEN COUNT(revision.id) = 0 THEN NULL
                    ELSE COALESCE(JSON_AGG(JSON_BUILD_OBJECT(
                        'user_id', revision.user_id,
                        'user_email', "user".email,
                        'modification_date', revision.date_created
                    ) ORDER BY revision.date_created DESC), '[]'::json)
                END as updates
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
                adsmanageradministrator.id = %s
            GROUP BY ads.id, adsmanager.id
            ORDER BY ads.last_update DESC
            LIMIT 100
        """,
            (self.kwargs["ads_manager_administrator"].id,),
        )
        updates = cursor.fetchall()

        # Load objects
        ads_objects = ADS.objects.filter(id__in=[row[0] for row in updates])
        ads_dict = {obj.id: obj for obj in ads_objects}

        ads_managers = ADSManager.objects.filter(
            id__in=[row[1] for row in updates]
        ).prefetch_related("content_type", "content_object")
        ads_managers_dict = {obj.id: obj for obj in ads_managers}
        return [
            {
                "ads": ads_dict[update[0]],
                "ads_manager": ads_managers_dict[update[1]],
                "history_entries": update[2],
            }
            for update in updates
        ]

    def get_context_data(self, *args, **kwargs):
        ctx = super().get_context_data(**kwargs)
        with connection.cursor() as cursor:
            ctx["updates"] = self.get_updates(cursor)
        return ctx
