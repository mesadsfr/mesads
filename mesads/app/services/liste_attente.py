from datetime import date

from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string

from mesads.app.models import ADSManagerRequest, InscriptionListeAttente


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

    email_subject = "Liste d'attente MesADS - Doublon d'inscription"
    email_content = render_to_string(
        "liste_attente/doublon_inscription_email_body.txt",
        {
            "inscription": inscription,
            "ads_manager": ads_manager,
            "base_url": settings.MESADS_BASE_URL,
        },
    )
    email_content_html = render_to_string(
        "liste_attente/doublon_inscription_email_body.mjml",
        {
            "inscription": inscription,
            "ads_manager": ads_manager,
            "base_url": settings.MESADS_BASE_URL,
        },
    )
    send_mail(
        email_subject,
        email_content,
        settings.MESADS_CONTACT_EMAIL,
        emails,
        fail_silently=True,
        html_message=email_content_html,
    )


def check_and_notify_duplicated(inscription: InscriptionListeAttente):
    duplicatas = inscription.get_duplicatas()

    if duplicatas.count() == 0:
        return

    inscriptions_a_notifier = list(duplicatas) + [inscription]

    for inscription_a_notifier in inscriptions_a_notifier:
        _notification_doublon(inscription_a_notifier)
