from mesads.app.models import InscriptionListeAttente, ADS, ADSUser, ADSManager
from django.contrib.postgres.aggregates import ArrayAgg
from django.db.models import Count, Q


def get_inscriptions_data_for_excel_export(ads_manager):
    fields = [
        "numero",
        "nom",
        "prenom",
        "numero_licence",
        "numero_telephone",
        "email",
        "adresse",
        "date_depot_inscription",
        "date_dernier_renouvellement",
        "date_fin_validite",
    ]

    headers = [
        "Numero",
        "Nom",
        "Prénom",
        "Numéro de carte professionnelle",
        "Numéro de téléphone",
        "Email",
        "Adresse",
        "Date de dépot d'inscription",
        "Date de dernier renouvellement",
        "Date de fin de validité",
    ]
    inscriptions = (
        InscriptionListeAttente.objects.filter(ads_manager=ads_manager)
        .order_by("-date_depot_inscription")
        .values_list(*fields)
    )

    return headers, inscriptions


def get_ads_data_for_excel_export(ads_manager=None, ads_manager_administrator=None):
    if ads_manager is None and ads_manager_administrator is None:
        raise ValueError("ads_manager or ads_manager_administrator must be defined")
    qs_ads = (
        ADS.objects.select_related(
            "ads_manager__administrator__prefecture",
        )
        .prefetch_related("ads_manager__content_object", "adslegalfile_set")
        .annotate(
            ads_users_status=ArrayAgg("adsuser__status"),
            ads_users_names=ArrayAgg("adsuser__name"),
            ads_users_sirets=ArrayAgg("adsuser__siret"),
            ads_users_licenses=ArrayAgg("adsuser__license_number"),
            legalfiles_count=Count("adslegalfile", distinct=True),
        )
        .order_by("ads_manager")
    )

    if ads_manager:
        qs_ads = qs_ads.filter(ads_manager=ads_manager)
    elif ads_manager_administrator:
        qs_ads = qs_ads.filter(ads_manager__administrator=ads_manager_administrator)

    base_headers = [
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
        "Nombre de documents enregistrés (arrêtés municipaux, …)",
    ]
    # If one of the ADS in the list has, let's say, 4 drivers, driver_headers
    # will be appended 4 times to headers.
    template_driver_headers = (
        "Statut du %s conducteur",
        "Nom du %s conducteur",
        "SIRET du %s conducteur",
        "Numéro de la carte professionnelle du %s conducteur",
    )

    # Counts the maximum number of drivers in the list of ADS..
    def drivers_count(a):
        # ArrayAgg peut renvoyer None si pas de lignes
        return len(a.ads_users_status or [])

    ads_list = list(qs_ads)
    max_drivers = max((drivers_count(a) for a in ads_list), default=0)

    def ORDINAL_FR(i):
        return "1er" if i == 1 else f"{i}e"

    driver_headers = [
        h % ORDINAL_FR(i)
        for i in range(1, max_drivers + 1)
        for h in template_driver_headers
    ]

    data = []

    status_label = dict(ADSUser.status.field.choices).get

    for ads in ads_list:
        row = [
            ads.ads_manager.content_object.type_name(),
            ads.ads_manager.content_object.text(),
            ads.number,
            ads.ads_in_use,
            ads.ads_creation_date,
            ads.ads_renew_date,
            ads.attribution_date,
            ads.accepted_cpam,
            ads.immatriculation_plate,
            ads.eco_vehicle,
            ads.vehicle_compatible_pmr,
            ads.owner_name,
            ads.owner_siret,
            ads.owner_phone,
            ads.owner_mobile,
            ads.owner_email,
            ads.legalfiles_count,
        ]
        for status, name, siret, licence in zip(
            ads.ads_users_status or [],
            ads.ads_users_names or [],
            ads.ads_users_sirets or [],
            ads.ads_users_licenses or [],
        ):
            row += [status_label(status, ""), name, siret, licence]
        data.append(row)

    # Write headers, now that we know the maximum number of drivers.
    headers = base_headers + driver_headers

    return headers, data


def get_gestionnaires_data_for_excel_export(ads_manager_administrator):
    headers = [
        "Nom de l'administration",
        "Nombre d'ADS",
        "Statut de la gestion des ADS",
        "Arrêté délimitant le nombre d'ADS",
    ]

    ads_managers = (
        ADSManager.objects.filter(administrator=ads_manager_administrator)
        .prefetch_related("content_object")
        .annotate(
            ads_count=Count(
                "ads", filter=Q(ads__deleted_at__isnull=True), distinct=True
            ),
            decrees_count=Count("adsmanagerdecree", distinct=True),
        )
    )

    def status_label(ads_manager):
        if ads_manager.no_ads_declared:
            return "L'administration a déclaré ne gérer aucune ADS"
        if ads_manager.epci_delegate_id:
            return f"La gestion des ADS est déléguée à {ads_manager.epci_delegate.display_fulltext()}"
        return ""

    def decrees_label(decrees_count):
        return (
            "1 document enregistré"
            if decrees_count == 1
            else f"{decrees_count} documents enregistrés"
        )

    rows = [
        [
            ads_manager.content_object.display_text(),
            ads_manager.ads_count,
            status_label(ads_manager),
            decrees_label(ads_manager.decrees_count),
        ]
        for ads_manager in ads_managers
    ]

    return headers, rows
