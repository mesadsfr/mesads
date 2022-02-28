from datetime import datetime
import json
import os
import pathlib
import re
from urllib.request import urlretrieve, HTTPError
import sys

import requests

from django.core.files import File
from django.core.management.base import BaseCommand

from mesads.app.models import ADS
from mesads.fradm.models import Commune


class Command(BaseCommand):
    help = (
        "Load ADS for Ille et Vilaine from info stored on demarches-simplfiees."
    )

    DEMARCHE_NUMBER = 35579

    # This query is given as an example in demarches-simplifiees.fr examples and
    # dumps all data of a demarche.
    # https://doc.demarches-simplifiees.fr/pour-aller-plus-loin/graphql
    GRAPHQL_QUERY = '''
    query getDemarche(
      $demarcheNumber: Int!
      $state: DossierState
      $order: Order
      $after: String
    ) {
      demarche(number: $demarcheNumber) {
        id
        number
        title
        publishedRevision {
          ...RevisionFragment
        }
        groupeInstructeurs {
          id
          number
          label
          instructeurs {
            id
            email
          }
        }
        dossiers(state: $state, order: $order, after: $after) {
          pageInfo {
            endCursor
            hasNextPage
          }
          nodes {
            ...DossierFragment
          }
        }
      }
    }

    query getGroupeInstructeur(
      $groupeInstructeurNumber: Int!
      $state: DossierState
      $order: Order
      $after: String
    ) {
      groupeInstructeur(number: $groupeInstructeurNumber) {
        id
        number
        label
        instructeurs {
          id
          email
        }
        dossiers(state: $state, order: $order, after: $after) {
          pageInfo {
            endCursor
            hasNextPage
          }
          nodes {
            ...DossierFragment
          }
        }
      }
    }

    query getDossier($dossierNumber: Int!) {
      dossier(number: $dossierNumber) {
        ...DossierFragment
        demarche {
          ...DemarcheDescriptorFragment
        }
      }
    }

    query getDeletedDossiers($demarcheNumber: Int!, $order: Order, $after: String) {
      demarche(number: $demarcheNumber) {
        deletedDossiers(order: $order, after: $after) {
          nodes {
            ...DeletedDossierFragment
          }
        }
      }
    }

    fragment DossierFragment on Dossier {
      id
      number
      archived
      state
      dateDerniereModification
      datePassageEnConstruction
      datePassageEnInstruction
      dateTraitement
      motivation
      motivationAttachment {
        ...FileFragment
      }
      attestation {
        ...FileFragment
      }
      pdf {
        url
      }
      instructeurs {
        email
      }
      groupeInstructeur {
        id
        number
        label
      }
      revision {
        ...RevisionFragment
      }
      champs {
        ...ChampFragment
        ...RootChampFragment
      }
      annotations {
        ...ChampFragment
        ...RootChampFragment
      }
      avis {
        ...AvisFragment
      }
      messages {
        ...MessageFragment
      }
      demandeur {
        ... on PersonnePhysique {
          civilite
          nom
          prenom
          dateDeNaissance
        }
        ...PersonneMoraleFragment
      }
    }

    fragment DemarcheDescriptorFragment on DemarcheDescriptor {
      id
      number
      title
      description
      state
      declarative
      dateCreation
      datePublication
      dateDerniereModification
      dateDepublication
      dateFermeture
    }

    fragment DeletedDossierFragment on DeletedDossier {
      id
      number
      dateSupression
      state
      reason
    }

    fragment RevisionFragment on Revision {
      id
      champDescriptors {
        ...ChampDescriptorFragment
        champDescriptors {
          ...ChampDescriptorFragment
        }
      }
      annotationDescriptors {
        ...ChampDescriptorFragment
        champDescriptors {
          ...ChampDescriptorFragment
        }
      }
    }

    fragment ChampDescriptorFragment on ChampDescriptor {
      id
      type
      label
      description
      required
      options
    }

    fragment AvisFragment on Avis {
      id
      question
      reponse
      dateQuestion
      dateReponse
      claimant {
        email
      }
      expert {
        email
      }
      attachment {
        ...FileFragment
      }
    }

    fragment MessageFragment on Message {
      id
      email
      body
      createdAt
      attachment {
        ...FileFragment
      }
    }

    fragment GeoAreaFragment on GeoArea {
      id
      source
      description
      geometry {
        type
        coordinates
      }
      ... on ParcelleCadastrale {
        commune
        numero
        section
        prefixe
        surface
      }
    }

    fragment RootChampFragment on Champ {
      ... on RepetitionChamp {
        champs {
          ...ChampFragment
        }
      }
      ... on SiretChamp {
        etablissement {
          ...PersonneMoraleFragment
        }
      }
      ... on CarteChamp {
        geoAreas {
          ...GeoAreaFragment
        }
      }
      ... on DossierLinkChamp {
        dossier {
          id
          state
          usager {
            email
          }
        }
      }
    }

    fragment ChampFragment on Champ {
      id
      label
      stringValue
      ... on DateChamp {
        date
      }
      ... on DatetimeChamp {
        datetime
      }
      ... on CheckboxChamp {
        checked: value
      }
      ... on DecimalNumberChamp {
        decimalNumber: value
      }
      ... on IntegerNumberChamp {
        integerNumber: value
      }
      ... on CiviliteChamp {
        civilite: value
      }
      ... on LinkedDropDownListChamp {
        primaryValue
        secondaryValue
      }
      ... on MultipleDropDownListChamp {
        values
      }
      ... on PieceJustificativeChamp {
        file {
          ...FileFragment
        }
      }
      ... on AddressChamp {
        address {
          ...AddressFragment
        }
      }
      ... on CommuneChamp {
        commune {
          name
          code
        }
        departement {
          name
          code
        }
      }
    }

    fragment PersonneMoraleFragment on PersonneMorale {
      siret
      siegeSocial
      naf
      libelleNaf
      address {
        ...AddressFragment
      }
      entreprise {
        siren
        capitalSocial
        numeroTvaIntracommunautaire
        formeJuridique
        formeJuridiqueCode
        nomCommercial
        raisonSociale
        siretSiegeSocial
        codeEffectifEntreprise
        dateCreation
        nom
        prenom
        attestationFiscaleAttachment {
          ...FileFragment
        }
        attestationSocialeAttachment {
          ...FileFragment
        }
      }
      association {
        rna
        titre
        objet
        dateCreation
        dateDeclaration
        datePublication
      }
    }

    fragment FileFragment on File {
      filename
      contentType
      checksum
      byteSizeBigInt
      url
    }

    fragment AddressFragment on Address {
      label
      type
      streetAddress
      streetNumber
      streetName
      postalCode
      cityName
      cityCode
      departmentName
      departmentCode
      regionName
      regionCode
    }
    '''

    def add_arguments(self, parser):
        parser.add_argument('--auth-token', required=True)

        # defaults to root directory
        parser.add_argument(
            '--cache-dir',
            default=(pathlib.Path(__file__) / '../../../../../.cache/ads-ille-et-vilaine').resolve()
        )

    def _log(self, level, msg):
        sys.stdout.write(level(f'{msg}\n'))

    def _get_pdf(self, dossier, **opts):
        """Get PDF stored in a dossier."""
        url = dossier['champs'][31]['file']['url']
        file_info = dossier['champs'][31]['file']
        checksum = file_info['checksum'].replace('/', '\\')
        cache_path = opts['cache_dir'] / f'{checksum}_{file_info["filename"]}'

        # If file not in cache, download and store it
        if not os.path.exists(cache_path):
            try:
                self._log(self.style.SUCCESS, f'Downloading PDF of dossier {dossier["id"]} to {cache_path}')
                urlretrieve(url, cache_path)
            except HTTPError:
                self._log(self.style.ERROR, (
                    f'Unable to download {url}.\n'
                    f'-> Try to remove {opts["cache_dir"]} and run this script again.\n'
                ))
                raise
        return cache_path

    def _load_demarche(self, after=None, **opts):
        """Load demarche from demarches-simplifiees.fr. Stores response in cache to speedup future runs."""
        cache_path = opts['cache_dir'] / ('api.json' if not after else f'api-after-{after}.json')

        # Load from cache.
        try:
            with open(cache_path) as handle:
                self._log(self.style.NOTICE, f'Load {cache_path} from cache')
                return json.loads(handle.read())
        except FileNotFoundError:
            pass

        variables = {
            'demarcheNumber': self.DEMARCHE_NUMBER,
            'after': after,
        }

        self._log(self.style.SUCCESS, f'Retrieving API after={after} and store in {cache_path}')

        # Load from API and store in cache.
        resp = requests.post(
            'https://www.demarches-simplifiees.fr/api/v2/graphql',
            data=json.dumps({
                'query': self.GRAPHQL_QUERY,
                'operationName': 'getDemarche',
                'variables': variables,
            }),
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {opts["auth_token"]}',
            }
        )
        content = resp.json()

        # Create root folders
        opts['cache_dir'].mkdir(parents=True, exist_ok=True)
        # Store file content
        with open(cache_path, 'w+') as handle:
            handle.write(json.dumps(content, indent=2))

        return content

    def _iterate_demarches(self, **opts):
        demarche = self._load_demarche(**opts)

        while True:
            for dossier in demarche['data']['demarche']['dossiers']['nodes']:
                yield dossier

            page_info = demarche['data']['demarche']['dossiers']['pageInfo']
            if not page_info['hasNextPage']:
                return

            demarche = self._load_demarche(after=page_info['endCursor'], **opts)

    def _parse_date(self, value):
        if not value:
            return None

        # Fix misspells: replace 20007 (three 0's) with 2007.
        res = re.match(r'^(\d)000(\d)-(.*)$', value)
        if res:
            value = f'{res.group(1)}00{res.group(2)}-{res.group(3)}'

        return datetime.strptime(value, '%Y-%m-%d').date()

    def _parse_bool(self, value, mandatory=False):
        if value.lower() == "oui":
            return True
        elif value.lower() == "non":
            return False
        elif value.lower() == "je ne sais pas" and not mandatory:
            return None
        raise ValueError(f"Invalid bool value {value}")

    def handle(self, *args, **opts):
        # Form does not provide stable identifiers for each field, so we have no other way than hardcoding the index of
        # each field. If the form changes, this script will break.
        for dossier in self._iterate_demarches(**opts):
            fields = dossier['champs']
            requester = fields[2]

            # In demarches simplifiees, address of the "Mairie" should be under " Identification de l'autorité ayant
            # délivré l'ADS " but for some files the taxi's company info has been provided. We have to ignore these
            # entries and create the ADS by hand.
            try:
                if requester['etablissement']['entreprise']['formeJuridique'] != 'Commune et commune nouvelle':
                    raise ValueError
            except:  # noqa
                self._log(
                    self.style.ERROR,
                    f'Dossier {dossier["number"]} is invalid: the authority of the ADS is not correct. It should be a '
                    f'"commune", and it is either not set or equal to the taxi\'s company'
                )
                continue

            commune = Commune.objects.filter(insee=requester['etablissement']['address']['cityCode']).get()

            # Our database models support a many to many relationship between ADSManager and Commune, but in reality
            # there is only one manager for a given Commune.
            #
            # If this line raises, it means there is more than one manager for the commune and we need a way to find
            # which one should be linked to the ADS created below.
            ads_manager = commune.ads_managers.get()

            ads_number = fields[6]['stringValue']

            ads, created = ADS.objects.get_or_create(ads_manager=ads_manager, number=ads_number)

            ads_creation_date = self._parse_date(fields[7]['date'])
            ads_attribution_date = self._parse_date(fields[9]['date'])

            if not created:
                if ads.ads_creation_date and not ads_creation_date:
                    self._log(
                        self.style.WARNING,
                        f'In database, ADS id {ads.id} (number {ads.number} for {ads_manager}) has a creation date set '
                        f'to {ads.ads_creation_date}. API provides data for this same ADS but without a creation date. '
                        f'This ADS returned from API is ignored.'
                    )
                    continue
                if ads.ads_creation_date and ads.ads_creation_date > ads_creation_date:
                    self._log(
                        self.style.WARNING,
                        f'In database, ADS id {ads.id} (number {ads.number} for {ads_manager}) has a creation date set '
                        f'to {ads.ads_creation_date}. API provides data for this same ADS, but with an older creation '
                        f'date of {ads_creation_date}. Since the API date is older than the value currently in '
                        f'database, we ignore this ADS entry.',
                    )
                    continue

            ads.ads_creation_date = ads_creation_date
            ads.attribution_date = ads_attribution_date

            ads.attribution_type = [
                key
                for key, value in ADS.ATTRIBUTION_TYPES
                if value == fields[10]['stringValue']
            ][0]

            ads.attribution_reason = fields[11]['stringValue']
            ads.accepted_cpam = self._parse_bool(fields[12]['stringValue'])
            ads.immatriculation_plate = fields[14]['stringValue']
            ads.vehicle_compatible_pmr = self._parse_bool(fields[15]['stringValue'])
            ads.eco_vehicle = self._parse_bool(fields[16]['stringValue'])
            ads.owner_firstname = fields[19]['stringValue']
            ads.owner_lastname = fields[20]['stringValue']

            if fields[21]['etablissement']:
                ads.owner_siret = fields[21]['etablissement']['siret']

            ads.used_by_owner = fields[22]['checked']
            ads.user_status = [
                key
                for key, value in ADS.ADS_USER_STATUS
                if value == fields[25]['stringValue']
            ][0]

            ads.user_name = fields[26]['stringValue']
            if fields[27]['etablissement']:
                ads.user_siret = fields[27]['etablissement']['siret']

            with open(self._get_pdf(dossier, **opts), 'rb') as pdf_handle:
                ads.legal_file = File(pdf_handle)
                ads.save()
