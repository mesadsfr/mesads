[![Tests unitaires](https://github.com/mesadsfr/mesads/actions/workflows/unittest.yml/badge.svg)](https://github.com/mesadsfr/mesads/actions/) [![codecov](https://codecov.io/gh/mesadsfr/mesads/branch/master/graph/badge.svg?token=2RT9SXITWB)](https://codecov.io/gh/mesadsfr/mesads) [![Vulnérabilités](https://snyk.io/test/github/mesadsfr/mesads/badge.svg)](https://snyk.io/test/github/mesadsfr/mesads/)

# MesADS

Ce dépôt contient le code source de MesADS, disponible sur https://mesads.beta.gouv.fr

MesADS est un service public numérique qui permet aux administrations de gérer les Autorisations de Stationnement (ADS) pour les taxis, et aux propriétaires de véhicules relais de les enregistrer.

## Registre ADS

Le code des transports définit un taxi comme un "véhicule automobile [...] dont le propriétaire ou l'exploitant est titulaire d’une autorisation de stationnement sur la voie publique, en attente de la clientèle, afin d’effectuer, à la demande de celle-ci et à titre onéreux, le transport particulier des personnes et de leurs bagages."

Les ADS — Autorisation De Stationnement — sont obtenues auprès de mairies où l'activité est exercée. Depuis octobre 2014, les licences sont incessibles (elles ne peuvent plus être vendues) et sont renouvelables tous les 5 ans.

### Fonctionnement

Afin d'utiliser Mes ADS, vous êtes dans une des situations suivantes :

- Vous représentez un gestionnaire d'ADS, c'est à dire une commune, préfecture ou EPCI délivrant des ADS : vous créez un compte et choisissez votre administration dans la liste déroulante. Un administrateur des gestionnaires d'ADS recevra votre demande. Après validation, vous pourrez lister et créer les ADS de votre administration.

- Vous représentez un administrateur des gestionnaires d'ADS, c'est à dire une préfecture : un compte vous a été fourni par l'équipe Mes ADS. Après connexion, vous pouvez lister les demandes des gestionnaires, lister l'intégralité des ADS au niveau national, et créer de nouvelles ADS dans les zones dépendant de votre préfecture (communes, gares, aéroports).

## Répertoire des véhicules relais

Un « taxi relais » est un véhicule utilisé temporairement en cas d'immobilisation d'origine mécanique, à la suite d'une panne ou d'un accident, ou de vol d'un véhicule taxi ou de ses équipements spéciaux.

### Fonctionnement

- Les propriétaires de véhicules relais doivent s'inscrire sur MesADS et activer leur espace propriétaire dans l'espace dédié. Il leur est alors possible d'enregistrer leurs véhicules relais.

- Le registre des véhicules relais est accessible sans authentification. Il suffit de sélectionner le département voulu pour voir la liste des véhicules relais enregistrés.


# Développement

```bash
$> make debug
# ou
$> make shell
# python manage.py runserver 0.0.0.0:8000
```

Le serveur est disponible sur http://localhost:9400

## Migrations

Pour passer les migrations de la base de données, exécutez depuis le container :

```bash
# python manage.py migrate
```

## Depuis les données de production

Pour importer les données de prod créez un fichier .local.env avec:

```
LOCAL_DATABASE=mesads

SUPERUSER_USERNAME=root@root.com
SUPERUSER_PASSWORD=password

# Paris, Ille-et-Villaine, Hérault
DEFAULT_ADS_MANAGER_ADMINISTRATOR="94 54 53"

# Melesse, Aast
DEFAULT_ADS_MANAGER="51431 62957"
```

Puis créez un fichier .prod.env avec:

```
DATA_FILE=mesads.sql
DB_USER=<prod user>
DB_PASSWORD=<prod password>
DB_HOST=<prod host>
DB_PORT=<prod port>
DB_NAME=<prod db name>

INSEE_TOKEN=<prod INSEE API token>

AWS_S3_ENDPOINT_URL=<prod AWS S3 credentials>
AWS_S3_ACCESS_KEY_ID=<prod AWS S3 credentials>
AWS_S3_SECRET_ACCESS_KEY=<prod AWS S3 credentials>
AWS_STORAGE_BUCKET_NAME=<prod AWS S3 credentials>
```

Enfin, lancez le script:

```bash
$> ./scripts/restore-prod-db-local.sh
```

## Accéder à la production

Certaines commandes, par exemple `import_last_update_file_from_paris`, nécessitent d'accéder aux fichiers sur S3. Le moyen le plus simple est d'utiliser le S3 de production.

```bash
$> set -a
$> source .prod.env
$> python manage.py import_last_update_file_from_paris
```

## Infrastructure

- L'application django, la base de données postgresql et le bucket S3 où sont stockés les arrêtés municipaux sont hébergés chez [Clever Cloud](https://www.clever-cloud.com/).
- Le sous-domaine mesads.beta.gouv.fr est géré sur [alwaysdata](www.alwaysdata.com) tel qu'expliqué [dans la documentation de beta.gouv](https://pad.incubateur.net/gg9OTDkhRnmSw-bnVr9WOg#).
- La boite email equipe@mesads.beta.gouv.fr configurée sur [alwaysdata](www.alwaysdata.com) transfère les emails reçus aux membres de l'équipe.
- [brevo](https://www.brevo.com/fr/) héberge le serveur SMTP utilisé pour les emails transactionnels .
- Afin d'avoir des sauvegardes chez plusieurs fournisseurs, les bases de données sont sauvegardées chez [Scaleway](https://www.scaleway.com/).
- Le support des utilisateurs est géré via [Crisp](https://crisp.chat/).
- Les exceptions en production sont remontées sur [Sentry](https://sentry.incubateur.net).
- Les statistiques de l'application sont remontées sur [Matomo](https://stats.beta.gouv.fr).

