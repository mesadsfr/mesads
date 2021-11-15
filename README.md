# Fonctionnement de MesADS

Je vais sur la page de création d'un compte et je remplis mon email et mon mot de passe.

Deux choix :

L'autorité existe déjà : je choisis une autorité à laquelle rattacher mon compte, par exemple : Préfecture de Police de Paris. Ma demande est en attente de validation, un compte gérant l'autorité doit la valider.

L'autorité n'existe pas : je créé l'autorité en précisant différentes données (nom, SIRET, ...). Un administrateur de MesADS doit maintenant valider que l'autorité est conforme.


Une fois que mon compte est validé par l'autorité, j'ai deux menus :

* Mes ADS : liste les ADS de l'autorité. Je peux rechercher les ADS par numéro, filtrer par type, ... Si je clique sur une ADS, je peux voir toutes les infos de l'ADS et modifier ou supprimer celle-ci.
* Nouvelle ADS : afin de créer une nouvelle entrée dans la base de données.

Si je suis un compte administrateur de l'autorité, j'ai un troisième menu : "Autorité de délivrance". La page me permet de valider les demandes d'accès à l'autorité, et passer un autre compte en administrateur.

En tant qu'administrateur de l'autorité, je peux aussi modifier les détails de mon autorité (SIRET, nom, ...).


La création d'une ADS se base sur démarches simplifiées : https://www.demarches-simplifiees.fr/admin/procedures/35579/apercu


Feature request:

* on pourrait intégrer des référentiels de communes, d'EPCI et de préfectures pour identifier les gestionnaires. Le SIRET un peu déjà cette fonction mais c'est un nombre. Je voudrais que ça soit basé un nom. par ex. "Mairie d'Aubervilliers" ou "Métropole Nice Côte d'Azur", ou encore "Préfecture de Police de Paris", avec un remplissage semi-automatique

  https://www.collectivites-locales.gouv.fr/institutions/liste-et-composition-des-epci-fiscalite-propre pour les EPCI
  https://www.insee.fr/fr/information/2028028 pour les communes
