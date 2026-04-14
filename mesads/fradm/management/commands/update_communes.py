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
        parser.add_argument("--gen-datafix", action=argparse.BooleanOptionalAction)

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
                    self.update_communes(
                        options["communes_file"], datafix, options["gen_datafix"]
                    )
                except Exception:
                    if options["shell"]:
                        traceback.print_exc()
                        breakpoint()
                    raise

    def update_communes(self, new_communes_file, datafix, gen_datafix=False):
        existing_communes = []

        # List all communes in existing_communes
        for commune in Commune.all_objects.all():
            existing_communes.append(commune)

        # Iterate over the file of new communes
        for row in csv.DictReader(new_communes_file):
            # Try to find the new commune in the existing communes. If one
            # exists, we remove it from the list of existing communes, and place
            # it in the list of similar communes.
            if row["DEP"] == "":
                if row["COM"].startswith("976"):
                    row["DEP"] = "976"
                else:
                    row["DEP"] = row["COM"][:2]

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
        # - InscriptionListeAttente
        ok = True
        communes_to_fix = []
        for commune in existing_communes:
            # Commune de test
            if commune.insee == "999":
                continue

            if datafix.get("communes") is not None:
                fix = datafix["communes"].get(int(commune.id))
                if fix:
                    new_commune = self.check_data_fix(fix, commune)
                    self.move_related_resources(commune, new_commune)

            ads_manager = ADSManager.objects.get(
                content_type=ContentType.objects.get_for_model(Commune),
                object_id=commune.id,
            )

            error = self.check_existing_data(commune, ads_manager)

            if error:
                ok = False
                communes_to_fix.append(commune)
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
            if gen_datafix:
                self.generate_datafix(communes_to_fix)
            raise ValueError("Mettre à jour le fichier datafix pour pouvoir continuer")

    def check_data_fix(self, fix_data, commune):
        if fix_data["insee"] != commune.insee or fix_data["libelle"] != commune.libelle:
            raise ValueError(
                "Problème dans le fichier datafix: insee or libelle différents "
                f"de la commune dans la db. Fix INSEE: {fix_data['insee']}, "
                f"Fix libelle: {fix_data['libelle']}, "
                f"Commune INSEE: {commune.insee}, "
                f"Commune libelle: {commune.libelle}"
            )
        try:
            q = Commune.all_objects.filter(
                insee=fix_data["new_owner"]["insee"],
                libelle=fix_data["new_owner"]["libelle"],
            )
            if fix_data["new_owner"].get("type"):
                q = q.filter(type_commune=fix_data["new_owner"]["type"])
            new_commune = q.get()
            return new_commune
        except Commune.MultipleObjectsReturned as exc:
            raise ValueError(
                "Dans le fichier datafix, trop de communes trouvées pour "
                f"new_owner.insee={fix_data['new_owner']['insee']} "
                f"new_owner.libelle={fix_data['new_owner']['libelle']}. "
                "Ajouter le type de la commune (par exemple type: COM) "
                "pour restreindre la recherche."
            ) from exc
        except Commune.DoesNotExist as exc:
            raise ValueError(
                "Dans le fichier datafix, new_owner.insee "
                f"({fix_data['new_owner']['insee']}) et "
                f"new_owner.libelle ({fix_data['new_owner']['libelle']}) "
                "ne correspondent à aucune commune dans la base de données. "
                "Vérifiez que les données sont correctes."
            ) from exc

    def check_existing_data(self, commune: Commune, ads_manager: ADSManager) -> bool:
        ads_manager_decrees_count = ads_manager.adsmanagerdecree_set.count()
        error = False
        if ads_manager_decrees_count != 0:
            print(
                f"Impossible de supprimer la commune id={commune.id} "
                f"ads_manager={ads_manager.id} insee={commune.insee} "
                f"libelle={commune.libelle} — {ads_manager_decrees_count} "
                "décret(s) lié(s)"
            )
            error = True

        ads_count = ads_manager.ads_set.count()
        if ads_count != 0:
            print(
                f"Impossible de supprimer la commune id={commune.id} "
                f"ads_manager={ads_manager.id} insee={commune.insee} "
                f"libelle={commune.libelle} — {ads_count} ADS liée(s)"
            )
            error = True

        ads_manager_requests_count = ads_manager.adsmanagerrequest_set.count()
        if ads_manager_requests_count != 0:
            print(
                f"Impossible de supprimer la commune id={commune.id} "
                f"ads_manager={ads_manager.id} insee={commune.insee} "
                f"libelle={commune.libelle} — {ads_manager_requests_count} "
                "demande(s) liée(s) pour devenir gestionnaire liées"
            )
            error = True

        inscriptions_count = ads_manager.inscriptions_liste_attente.count()
        if inscriptions_count != 0:
            print(
                f"Impossible de supprimer la commune id={commune.id} "
                f"ads_manager={ads_manager.id} insee={commune.insee} "
                f"libelle={commune.libelle} — {inscriptions_count} "
                "inscriptions liste attente liées"
            )
            error = True

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
            error = True

        return error

    def generate_datafix(self, communes_to_fix):
        data = {"communes": {}}
        for commune in communes_to_fix:
            data["communes"][commune.id] = {
                "insee": commune.insee,
                "libelle": commune.libelle,
                "new_owner": {
                    "insee": "XXXX",
                    "libelle": "XXXX",
                },
            }

        with open("DATAFIX_TO_FILL.yml", "w", encoding="utf-8") as f:
            yaml.dump(
                data,
                f,
                allow_unicode=True,
                sort_keys=False,
                default_flow_style=False,
            )

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

        for vehicule in Vehicule.with_deleted.filter(commune_localisation=old_commune):
            vehicule.commune_localisation = new_commune
            vehicule.save()

        for inscription in old_ads_manager.inscriptions_liste_attente.all():
            inscription.ads_manager = new_commune
            inscription.save()
