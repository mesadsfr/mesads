[![Tests unitaires](https://github.com/mesadsfr/mesads/actions/workflows/unittest.yml/badge.svg)](https://github.com/mesadsfr/mesads/actions/) [![codecov](https://codecov.io/gh/mesadsfr/mesads/branch/master/graph/badge.svg?token=2RT9SXITWB)](https://codecov.io/gh/mesadsfr/mesads) [![Vulnérabilités](https://snyk.io/test/github/mesadsfr/mesads/badge.svg)](https://snyk.io/test/github/mesadsfr/mesads/)

# Fonctionnement de Mes ADS

Ce dépôt contient le code source de MesADS, disponible sur https://mesads.beta.gouv.fr

# Contexte

Le code des transports définit un taxi comme un "véhicule automobile [...] dont le propriétaire ou l'exploitant est titulaire d’une autorisation de stationnement sur la voie publique, en attente de la clientèle, afin d’effectuer, à la demande de celle-ci et à titre onéreux, le transport particulier des personnes et de leurs bagages."

Les ADS — Autorisation De Stationnement — sont obtenues auprès de mairies où l'activité est exercée. Depuis octobre 2014, les licences sont incessibles (elles ne peuvent plus être vendues) et sont renouvelables tous les 5 ans.


# Fonctionnement

Afin d'utiliser Mes ADS, vous êtes dans une des situations suivantes :

* Vous représentez un gestionnaire d'ADS, c'est à dire une commune, préfecture ou EPCI délivrant des ADS : vous créez un compte et choisissez votre administration dans la liste déroulante. Un administrateur des gestionnaires d'ADS recevra votre demande. Après validation, vous pourrez lister et créer les ADS de votre administration.

* Vous représentez un administrateur des gestionnaires d'ADS, c'est à dire une préfecture : un compte vous a été fourni par l'équipe Mes ADS. Après connexion, vous pouvez lister les demandes des gestionnaires, lister l'intégralité des ADS au niveau national, et créer de nouvelles ADS dans les zones dépendant de votre préfecture (communes, gares, aéroports).


# Développement

```bash
$> make debug
# ou
$> make shell
# python manage.py runserver 0.0.0.0:8000
```

Le serveur est disponible sur http://localhost:9400

Pour passer les migrations de la base de données, exécutez depuis le container :

```bash
# python manage.py migrate
```

Pour importer les données initiales (respectez l'ordre) :

```bash
# python manage.py load_communes
# python manage.py load_epci
# python manage.py load_prefectures
# python manage.py load_ads_managers
```

Pour importer les données de prod créez un fichier .local.env avec:

```
LOCAL_DATABASE=mesads

SUPERUSER_USERNAME=root@root.com
SUPERUSER_PASSWORD=password

# Paris, Ille-et-Villaine, Hérault
DEFAULT_ADS_MANAGER_ADMINISTRATOR="94 54 53"

# Melesse, Aast
DEFAULT_ADS_MANAGER="51431 62957"%
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
# ./scripts/restore-prod-db-local.sh
```

# Ressources

Liste des EPCI, "établissement public de coopération intercommunale":

  * https://www.collectivites-locales.gouv.fr/institutions/liste-et-composition-des-epci-fiscalite-propre


Liste des départements, préfectures, communes :

  * https://www.insee.fr/fr/information/5057840
  * https://www.insee.fr/fr/statistiques/fichier/5057840/departement2021-csv.zip


# Ressources géographiques

Liste des départements

  * https://www.data.gouv.fr/fr/datasets/contours-des-departements-francais-issus-d-openstreetmap/

# Infrastructure

* L'application django, la base de données postgresql et le bucket S3 où sont stockés les arrêtés municipaux sont hébergés chez [Clever Cloud](https://www.clever-cloud.com/).
* Le sous-domaine mesads.beta.gouv.fr est géré sur [alwaysdata](www.alwaysdata.com) tel qu'expliqué [dans la documentation de beta.gouv](https://pad.incubateur.net/gg9OTDkhRnmSw-bnVr9WOg#).
* La boite email equipe@mesads.beta.gouv.fr configurée sur [alwaysdata](www.alwaysdata.com) transfère les emails reçus aux membres de l'équipe.
* [sendinblue](https://fr.sendinblue.com/) héberge le serveur SMTP utilisé pour les emails transactionnels .