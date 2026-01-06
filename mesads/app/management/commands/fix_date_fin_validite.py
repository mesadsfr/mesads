from django.core.management.base import BaseCommand
from django.db import transaction

from mesads.app.forms import compute_next_date_fin_validite
from mesads.app.models import InscriptionListeAttente


class Command(BaseCommand):
    help = "Commande pour fixer les mauvaises date de fin de validité"

    def handle(self, *args, **options):
        with transaction.atomic():
            for inscription in InscriptionListeAttente.objects.all():
                inscription.date_fin_validite = compute_next_date_fin_validite(
                    inscription.date_depot_inscription,
                    inscription.date_dernier_renouvellement,
                )
                inscription.save()
