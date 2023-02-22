import csv
import sys

from django.core.management.base import BaseCommand
from django.db.models import Count

from mesads.app.models import ADS, ADSUser


class Command(BaseCommand):
    help = 'Temporary script to fix ADSUser objects.'

    def add_arguments(self, parser):
        parser.add_argument('--csv', action='store_true', default=False, help='Output CSV instead of text.')

    def handle(self, **options):
        """ADS has a flag used_by_owner to indicate whether the ADS is operated
        by the owner or not.

        If not, user can specify one or several ADSUser objects who operate the
        ADS.

        When the flag is true, it was previously not possible to provide the
        owner's professional license number as the column to store this number
        didn't exist. To provide the number, administrations used to set the
        flag to false or null and create a new ADSUser object with the owner's
        name and license number.

        This script fixes the ADSUser objects created in this way.
        """
        bools_icons = {
            True: "✅",
            False: "❌",
            None: "❓",
        }

        if options['csv']:
            output = csv.writer(sys.stdout)
            output.writerow([
                'URL',
                'Préfecture',
                'Administration',
                'ADS ID',
                'ADS exploitée par le titulaire ?',
                'Statut exploitant',
                'Nom titulaire',
                'SIRET titulaire',
                'Nom exploitant',
                'SIRET exploitant',
                'N° de licence exploitant',
                'SIRETs titulaire et exploitant identiques ?',
                'Nom titulaire et exploitant identiques ?',
                'Nom titulaire vide ?',
                'Nom exploitant vide ?',
            ])

            def display(ads, ads_user):
                output.writerow([
                    f'https://mesads.beta.gouv.fr/admin/app/ads/{ads.id}/change/',
                    ads.ads_manager.administrator.prefecture.display_text(),
                    ads.ads_manager.content_object.display_text(),
                    ads.id,
                    bools_icons[ads.used_by_owner],
                    ads_user.status,
                    ads.owner_name.replace('\n', ' '),
                    ads.owner_siret,
                    ads_user.name.replace('\n', ' '),
                    ads_user.siret,
                    ads_user.license_number,
                    ads.owner_siret == ads_user.siret,
                    sorted(ads.owner_name.strip().lower().split()) == sorted(ads_user.name.strip().lower().split()),
                    self.is_empty_name(ads.owner_name),
                    self.is_empty_name(ads_user.name),
                ])
        else:
            def display(ads, ads_user):
                url = f'https://mesads.beta.gouv.fr/admin/app/ads/{ads.id}/change/'
                sys.stdout.write(f'{url:<60} | {f"{ads.id} - {bools_icons[ads.used_by_owner]} {ads_user.status}":<38} | {bools_icons[ads.owner_siret == ads_user.siret]} owner_name="{ads.owner_name}" owner_siret="{ads.owner_siret}" user_name="{ads_user.name}" user_siret="{ads_user.siret}" user_license_number="{ads_user.license_number}"\n')

        # Get all ADS objects with only one ADSUser object
        ads_w_one_adsuser = ADS.objects.annotate(
            adsuser_count=Count('adsuser')
        ).filter(adsuser_count=1)

        for ads in ads_w_one_adsuser:
            ads_user = ads.adsuser_set.first()
            self.fix_ads(ads, ads_user, display)

    def fix_ads(self, ads, ads_user, display_ads):
        if (

            ads.owner_siret == ads_user.siret
            and (ads.used_by_owner is True or ads.used_by_owner is None)
            and (ads_user.status == 'titulaire_exploitant' or ads_user.status is None)
            # make Jean Dupont and Dupont Jean equal
            and sorted(ads.owner_name.strip().lower().split()) == sorted(ads_user.name.strip().lower().split())
        ):
            display_ads(ads, ads_user)
            ads.used_by_owner = True
            ads.owner_license_number = ads_user.license_number
            ads.save()
            ads_user.delete()

    def is_empty_name(self, name):
        """Return True if name is empty or contains only spaces or dashes."""
        name = name.replace('-', '')
        name = name.strip()
        return not name
