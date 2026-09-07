from datetime import date

from django.core.management.base import BaseCommand

from mesads.app.models import ADSManagerAdministrator, DemandeGestionPrefecture


class Command(BaseCommand):
    help = ()

    def transfert_users_prefecture(self, administrator: ADSManagerAdministrator):
        for user in administrator.users.all():
            demande = DemandeGestionPrefecture.objects.filter(user=user).first()
            if demande:
                if demande.statut != DemandeGestionPrefecture.ACCEPTE:
                    demande.statut = DemandeGestionPrefecture.ACCEPTE
                    demande.accepted_at = date.today()
                    demande.save()

            else:
                DemandeGestionPrefecture.objects.create(
                    user=user,
                    administrator=administrator,
                    statut=DemandeGestionPrefecture.ACCEPTE,
                    accepted_at=date.today(),
                )

    def handle(self, *args, **options):
        for administrator in ADSManagerAdministrator.objects.all():
            self.transfert_users_prefecture(administrator)
