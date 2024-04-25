from django.contrib.postgres.aggregates import ArrayAgg
from django.http import HttpResponse

import xlsxwriter

from ..models import (
    ADS,
    ADSUser,
)


class ADSExporter:
    """Generic class to export a list of ADS in an Excel file."""

    def get_filename(self):
        raise NotImplementedError

    def get_queryset(self):
        return (
            ADS.objects.select_related(
                "ads_manager__administrator__prefecture",
            )
            .prefetch_related(
                "ads_manager__content_object",
            )
            .annotate(
                ads_users_status=ArrayAgg("adsuser__status"),
                ads_users_names=ArrayAgg("adsuser__name"),
                ads_users_sirets=ArrayAgg("adsuser__siret"),
                ads_users_licenses=ArrayAgg("adsuser__license_number"),
            )
        )

    def display_bool(self, value):
        if value is None:
            return ""
        return "oui" if value else "non"

    def display_date(self, value):
        if not value:
            return ""
        return value.strftime("%d/%m/%Y")

    def generate(self):
        response = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f'attachment; filename="{self.get_filename()}"'
            },
        )
        workbook = xlsxwriter.Workbook(response)
        self.add_sheets(workbook)
        workbook.close()
        return response

    def add_sheets(self, workbook):
        """Override this method to add more sheets to the workbook."""
        self.ads_list_sheet(workbook)

    def ads_list_sheet(self, workbook):
        bold_format = workbook.add_format({"bold": True})
        sheet = workbook.add_worksheet("ADS enregistrées")
        headers = (
            "Type d'administration",
            "Administration",
            "Numéro de l'ADS",
            "ADS actuellement exploitée ?",
            "Date de création de l'ADS",
            "Date du dernier renouvellement de l'ADS",
            "Date d'attribution de l'ADS au titulaire actuel",
            "Véhicule conventionné CPAM ?",
            "Plaque d'immatriculation du véhicule",
            "Le véhicule est-il un véhicule électrique/hybride ?",
            "Véhicule compatible PMR ?",
            "Titulaire de l'ADS",
            "SIRET du titulaire de l'ADS",
            "Téléphone fixe du titulaire de l'ADS",
            "Téléphone mobile du titulaire de l'ADS",
            "Email du titulaire de l'ADS",
        )
        # If one of the ADS in the list has, let's say, 4 drivers, driver_headers
        # will be appended 4 times to headers.
        driver_headers = (
            "Statut du %s conducteur",
            "Nom du %s conducteur",
            "SIRET du %s conducteur",
            "Numéro de la carte professionnelle du %s conducteur",
        )
        # Counts the maximum number of drivers in the list of ADS..
        max_drivers = 0

        # Applying bold format to headers
        sheet.set_row(0, None, bold_format)

        for idx, ads in enumerate(self.get_queryset()):
            # Append driver headers to headers if the current ADS has more drivers
            # than the previous ones.
            while max_drivers < len(ads.ads_users_status):
                for h in driver_headers:
                    headers += (
                        h % ("1er" if max_drivers == 0 else "%se" % (max_drivers + 1)),
                    )
                max_drivers += 1

            info = (
                ads.ads_manager.content_object.type_name(),
                ads.ads_manager.content_object.text(),
                ads.number,
                self.display_bool(ads.ads_in_use),
                self.display_date(ads.ads_creation_date),
                self.display_date(ads.ads_renew_date),
                self.display_date(ads.attribution_date),
                self.display_bool(ads.accepted_cpam),
                ads.immatriculation_plate,
                self.display_bool(ads.eco_vehicle),
                self.display_bool(ads.vehicle_compatible_pmr),
                ads.owner_name,
                ads.owner_siret,
                ads.owner_phone,
                ads.owner_mobile,
                ads.owner_email,
            )
            for nth, status in enumerate(ads.ads_users_status):
                # ads_users_status, ads_users_names, ads_users_sirets and
                # ads_users_licenses have the same length.
                info += (
                    dict(ADSUser.status.field.choices).get(
                        ads.ads_users_status[nth], ""
                    ),
                    ads.ads_users_names[nth],
                    ads.ads_users_sirets[nth],
                    ads.ads_users_licenses[nth],
                )
            sheet.write_row(idx + 1, 0, info)

        # Write headers, now that we know the maximum number of drivers.
        sheet.write_row(0, 0, headers)
        sheet.autofit()
