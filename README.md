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

Si vous souhaitez importer les données de l'Ille et Vilaine stockées sur demarches-simplfiees :

```bash
# python manage.py load_ads_from_ille_et_vilaine --auth-token=xxx
```

# Ressources

Formulaire existant sur démarches simplifiées pour les ADS de l'Ille et Vilaine :

  * https://www.demarches-simplifiees.fr/admin/procedures/35579/apercu


Liste des EPCI, "établissement public de coopération intercommunale":

  * https://www.collectivites-locales.gouv.fr/institutions/liste-et-composition-des-epci-fiscalite-propre


Liste des départements, préfectures, communes :

  * https://www.insee.fr/fr/information/5057840
  * https://www.insee.fr/fr/statistiques/fichier/5057840/departement2021-csv.zip
