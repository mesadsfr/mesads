# Fonctionnement de MesADS


# Contexte

Le code des transports définit un taxi comme un "véhicule automobile [...] dont le propriétaire ou l'exploitant est titulaire d’une autorisation de stationnement sur la voie publique, en attente de la clientèle, afin d’effectuer, à la demande de celle-ci et à titre onéreux, le transport particulier des personnes et de leurs bagages."

Les ADS — Autorisation De Stationnement — sont obtenues auprès de mairies où l'activité est exercée. Depuis octobre 2014, les licences sont incessibles (elles ne peuvent plus être vendues) et sont renouvelables tous les 5 ans.


# Fonctionnement

Afin d'utiliser MesADS, vous êtes dans une des situations suivantes :

* Vous représentez un gestionnaire d'ADS, c'est à dire une commune délivrant des ADS : vous créez un compte et choisissez votre commune dans la liste déroulante. Un administrateur des gestionnaires d'ADS recevra votre demande. Après validation, vous pourrez lister et créer les ADS de votre commune.

* Vous représentez un administrateur des gestionnaires d'ADS, c'est à dire une préfecture : un compte vous a été fourni par l'équipe MesADS. Après connexion, vous pouvez lister les demandes des gestionnaires, lister l'intégralité des ADS au niveau national, et créer de nouvelles ADS dans les zones dépendant de votre préfecture (communes, gares, aéroports).


# Ressources

Formulaire existant sur démarches simplifiées :

  * https://www.demarches-simplifiees.fr/admin/procedures/35579/apercu


Liste des EPCI, "établissement public de coopération intercommunale":

  * https://www.collectivites-locales.gouv.fr/institutions/liste-et-composition-des-epci-fiscalite-propre


Liste des départements, préfectures, communes :

  * https://www.insee.fr/fr/information/5057840
  * https://www.insee.fr/fr/statistiques/fichier/5057840/departement2021-csv.zip


# TODO

* Vérifier que les models correspondent à demarches-simplifiees
* Voir comment importer la liste des departements/communes/epci


Notes:

    Liste des administrateur gestionnaires d'ADS : Liste des prefectures, mais changer Paris en Prefecture de Police de Paris


    Liste des gestionnaires d'ADS :

    * toutes les prefectures (pour les aéroports, gare)
    * toutes les EPCI
    * toutes les communes

    Sur 36000 communes en france, on a seulement 12k gestionnaires ads masi on ne sait pas qui



    Lorsqu'un gestionnaire d'ADS s'enregistre, il spécifie sa prefecture, epci ou commune et sa prefecture de rattachement
    Lorsqu'un gestionaire s'enregistre et est lui même une prefecture, pas besoin de spécifier une prefecture


    Definition prefecture

    * juste le nom


    CA communauté agglo
    CC communauté commune
    CU communauté urbaine


    Déifnition commune

    NCCCENR
    COM = code insee
