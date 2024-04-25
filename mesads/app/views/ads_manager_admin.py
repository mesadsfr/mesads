from django.shortcuts import get_object_or_404
from django.utils.text import slugify
from django.views.generic import View

from ..models import (
    ADSManager,
)

from .export import ADSExporter


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
            self.ads_manager_administrator.adsmanager_set.all()
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
