import argparse
import csv
import os
import re
import traceback

import yaml
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction

from mesads.app.models import ADS, ADSManager, ADSManagerAdministrator
from mesads.fradm.models import Commune
from mesads.vehicules_relais.models import Vehicule


class Command(BaseCommand):
    help = "Mise à jour de la liste des communes dans la base de données."

    def add_arguments(self, parser):
        parser.add_argument("communes_file", type=argparse.FileType("r"))
        parser.add_argument("datafix_file", type=argparse.FileType("r"))
        parser.add_argument("--shell", action=argparse.BooleanOptionalAction)

    def handle(self, *args, **options):
        if not re.match(
            r"v_commune_\d+.csv", os.path.basename(options["communes_file"].name)
        ):
            raise CommandError(
                (
                    'L\'INSEE appelle le fichier de communes "v_commune_<year>.csv".'
                    f" Le fichier fourni ({options['communes_file'].name}) "
                    "est a priori incorrect."
                )
            )
        if not re.match(r".*.ya?ml$", os.path.basename(options["datafix_file"].name)):
            raise CommandError(
                f'Fichier datafix "{options["datafix_file"].name}" '
                "incorrect. Doit être un fichier YAML."
            )

        datafix = yaml.safe_load(options["datafix_file"])

        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute("SET CONSTRAINTS ALL DEFERRED")

                try:
                    self.update_communes(options["communes_file"], datafix)
                except Exception:
                    if options["shell"]:
                        traceback.print_exc()
                        breakpoint()
                    raise

    def update_communes(self, new_communes_file, datafix):
        existing_communes = []

        # List all communes in existing_communes
        for commune in Commune.all_objects.all():
            existing_communes.append(commune)

        # Iterate over the file of new communes
        for row in csv.DictReader(new_communes_file):
            # Try to find the new commune in the existing communes. If one
            # exists, we remove it from the list of existing communes, and place
            # it in the list of similar communes.
            for commune in existing_communes:
                if (
                    commune.insee == row["COM"]
                    and commune.type_commune == row["TYPECOM"]
                    and commune.departement == row["DEP"]
                    and commune.libelle == row["LIBELLE"]
                ):
                    existing_communes.remove(commune)
                    break
            # This case is for a commune that has not been found in the existing
            # communes. We need to insert it.
            else:
                if row["DEP"] == "":
                    if row["COM"].startswith("976"):
                        row["DEP"] = "976"
                    else:
                        row["DEP"] = row["COM"][:2]

                new_commune = Commune(
                    insee=row["COM"],
                    departement=row["DEP"],
                    libelle=row["LIBELLE"],
                    type_commune=row["TYPECOM"],
                )
                new_commune.save()

                administrator = ADSManagerAdministrator.objects.get(
                    # Don't ask me why, but some entries in the file have a DEP
                    # column empty. In this case, the departement number is
                    # retrieved from the first 2 chars of the INSEE code.
                    prefecture__numero=row["DEP"] or row["COM"][:2]
                )

                ADSManager.objects.create(
                    administrator=administrator,
                    content_type=ContentType.objects.get_for_model(Commune),
                    object_id=new_commune.id,
                )

        # existing_communes now contains all the communes that are in the database,
        # but are not in the new file.
        # For each of these communes, we check if there is an entry in the
        # datafix file to move the resources linked to another commune.
        #
        # If there is no entry and the commune has linked resources, we raise an
        # error. Otherwise, we can safely remove the commune.
        #
        # The related resources of a commune are:
        # - ADS
        # - ADSManagerDecree
        # - ADSManagerRequest
        # - Vehicule
        ok = True
        for commune in existing_communes:
            # Commune de test
            if commune.insee == "999":
                continue

            fix = datafix["communes"].get(int(commune.id))
            if fix:
                if fix["insee"] != commune.insee or fix["libelle"] != commune.libelle:
                    raise ValueError(
                        "Problème dans le fichier datafix: insee or libelle différents "
                        f"de la commune dans la db. Fix INSEE: {fix['insee']}, "
                        f"Fix libelle: {fix['libelle']}, "
                        f"Commune INSEE: {commune.insee}, "
                        f"Commune libelle: {commune.libelle}"
                    )
                try:
                    q = Commune.all_objects.filter(
                        insee=fix["new_owner"]["insee"],
                        libelle=fix["new_owner"]["libelle"],
                    )
                    if fix["new_owner"].get("type"):
                        q = q.filter(type_commune=fix["new_owner"]["type"])
                    new_commune = q.get()
                except Commune.MultipleObjectsReturned as exc:
                    raise ValueError(
                        "Dans le fichier datafix, trop de communes trouvées pour "
                        f"new_owner.insee={fix['new_owner']['insee']} "
                        f"new_owner.libelle={fix['new_owner']['libelle']}. "
                        "Ajouter le type de la commune (par exemple type: COM) "
                        "pour restreindre la recherche."
                    ) from exc
                except Commune.DoesNotExist as exc:
                    raise ValueError(
                        "Dans le fichier datafix, new_owner.insee "
                        f"({fix['new_owner']['insee']}) et "
                        f"new_owner.libelle ({fix['new_owner']['libelle']}) "
                        "ne correspondent à aucune commune dans la base de données. "
                        "Vérifiez que les données sont correctes."
                    ) from exc

                self.move_related_resources(commune, new_commune)

            ads_manager = ADSManager.objects.get(
                content_type=ContentType.objects.get_for_model(Commune),
                object_id=commune.id,
            )

            err = False

            ads_manager_decrees_count = ads_manager.adsmanagerdecree_set.count()
            if ads_manager_decrees_count != 0:
                print(
                    f"Impossible de supprimer la commune id={commune.id} "
                    f"ads_manager={ads_manager.id} insee={commune.insee} "
                    f"libelle={commune.libelle} — {ads_manager_decrees_count} "
                    "décret(s) lié(s)"
                )
                err = True

            ads_count = ads_manager.ads_set.count()
            if ads_count != 0:
                print(
                    f"Impossible de supprimer la commune id={commune.id} "
                    f"ads_manager={ads_manager.id} insee={commune.insee} "
                    f"libelle={commune.libelle} — {ads_count} ADS liée(s)"
                )
                err = True

            ads_manager_requests_count = ads_manager.adsmanagerrequest_set.count()
            if ads_manager_requests_count != 0:
                print(
                    f"Impossible de supprimer la commune id={commune.id} "
                    f"ads_manager={ads_manager.id} insee={commune.insee} "
                    f"libelle={commune.libelle} — {ads_manager_requests_count} "
                    "demande(s) liée(s) pour devenir gestionnaire liées"
                )
                err = True

            vehicules_relais_count = Vehicule.objects.filter(
                commune_localisation=commune
            ).count()
            if vehicules_relais_count != 0:
                print(
                    f"Impossible de supprimer la commune id={commune.id} "
                    f"ads_manager={ads_manager.id} insee={commune.insee} "
                    f"libelle={commune.libelle} — {vehicules_relais_count} "
                    "véhicule(s) relais lié(s)"
                )
                err = True

            if err:
                ok = False
                print("--")
            else:
                try:
                    commune.delete()
                except Exception as e:
                    print(
                        f"Impossible de supprimer la commune id={commune.id} "
                        f"ads_manager={ads_manager.id} insee={commune.insee} "
                        f"libelle={commune.libelle} — {e}"
                    )
                    print("--")
                    ok = False

        if not ok:
            raise ValueError("Mettre à jour le fichier datafix pour pouvoir continuer")

    def move_related_resources(self, old_commune, new_commune):
        old_ads_manager = ADSManager.objects.get(
            content_type=ContentType.objects.get_for_model(Commune),
            object_id=old_commune.id,
        )
        new_ads_manager = ADSManager.objects.get(
            content_type=ContentType.objects.get_for_model(Commune),
            object_id=new_commune.id,
        )

        for decree in old_ads_manager.adsmanagerdecree_set.all():
            decree.ads_manager = new_ads_manager
            decree.save()

        for ads in old_ads_manager.ads_set.all():
            ads.ads_manager = new_ads_manager
            ads.save()

        for ads in ADS.objects.filter(epci_commune=old_commune):
            ads.epci_commune = new_commune
            ads.save()

        for ads_manager_request in old_ads_manager.adsmanagerrequest_set.all():
            ads_manager_request.ads_manager = new_ads_manager
            ads_manager_request.save()

        for vehicule in Vehicule.objects.filter(commune_localisation=old_commune):
            vehicule.commune_localisation = new_commune
            vehicule.save()
