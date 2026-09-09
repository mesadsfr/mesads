from datetime import date

from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.utils import timezone

from mesads.app.models import ADSManagerRequest, InscriptionListeAttente
from mesads.common.mail import envoi_email


def compute_next_date_fin_validite(
    date_debut: date, date_renouvellement: date | None = None
) -> date:
    if date_renouvellement is None or date_renouvellement <= date_debut:
        return date_debut + relativedelta(years=1)

    date_candidate = date_debut + relativedelta(
        years=date_renouvellement.year - date_debut.year
    )

    if date_candidate < date_renouvellement:
        return date_candidate + relativedelta(years=2)
    return date_candidate + relativedelta(years=1)


def set_next_date_fin_validite(obj: InscriptionListeAttente):
    obj.date_fin_validite = compute_next_date_fin_validite(
        obj.date_depot_inscription, obj.date_dernier_renouvellement
    )


def _notification_doublon(inscription: InscriptionListeAttente):
    ads_manager = inscription.ads_manager
    ads_manager_requests = ADSManagerRequest.objects.filter(
        ads_manager=ads_manager, accepted=True
    )
    emails = [
        ads_manager_request.user.email for ads_manager_request in ads_manager_requests
    ]

    envoi_email(
        content_template_txt="liste_attente/doublon_inscription_email_body.txt",
        content_template_mjml="liste_attente/doublon_inscription_email_body.mjml",
        context={
            "inscription": inscription,
            "ads_manager": ads_manager,
            "base_url": settings.MESADS_BASE_URL,
        },
        destinataires=emails,
        sujet="Liste d'attente MesADS - Doublon d'inscription",
    )


def check_and_notify_duplicated(inscription: InscriptionListeAttente):
    duplicatas = inscription.get_duplicatas()

    if duplicatas.count() == 0:
        return

    inscriptions_a_notifier = list(duplicatas) + [inscription]

    for inscription_a_notifier in inscriptions_a_notifier:
        _notification_doublon(inscription_a_notifier)


def supression_inscriptions_archivees():
    """
    Fonction qui va supprimer les inscriptions à la liste d'attente
    archivées depuis plus de 6 mois.
    """

    date_limite = timezone.now() - relativedelta(months=6)

    inscriptions = InscriptionListeAttente.with_deleted.filter(
        deleted_at__isnull=False, deleted_at__lt=date_limite
    )
    inscriptions_count = inscriptions.count()
    inscriptions.delete()

    return inscriptions_count
