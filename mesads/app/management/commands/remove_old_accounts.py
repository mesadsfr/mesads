from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from mesads.app.models import ADSManagerAdministrator, ADSManagerRequest
from mesads.users.models import User
from mesads.vehicules_relais.models import Proprietaire


class Command(BaseCommand):
    help = ()

    def handle(self, **opts):
        six_months_ago = timezone.now() - timedelta(days=180)
        users = User.objects.filter(
            is_active=False, last_login=None, date_joined__lt=six_months_ago
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Trouvé {users.count()} utilisateurs inactifs depuis plus de 6 mois "
                f"qui n'ont pas de date de connexion enregistrée"
            )
        )

        for user in users:
            is_ads_manager_administrator = ADSManagerAdministrator.objects.filter(
                users__in=[user]
            ).count()
            if is_ads_manager_administrator:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"{user.email} a un compte administrateur de gestionnaire ADS, "
                        "pas de suppression"
                    )
                )
                continue

            is_ads_manager = ADSManagerRequest.objects.filter(user=user).count()
            if is_ads_manager:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"{user.email} a une demande pour devenir gestionnaire ADS, "
                        "pas de suppression"
                    )
                )
                continue

            is_proprietaire = Proprietaire.objects.filter(users__in=[user]).count()
            if is_proprietaire:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"{user.email} a un compte propriétaire de véhicules relais, "
                        "pas de suppression"
                    )
                )
                continue

            user.delete()
            self.stdout.write(self.style.SUCCESS(f"Utilisateur {user.email} supprimé"))
