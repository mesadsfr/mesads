import factory
import random

from datetime import timedelta
from dateutil.relativedelta import relativedelta
from django.utils import timezone

from mesads.app.models import (
    ADSManagerAdministrator,
    ADSManager,
    ADSManagerRequest,
    InscriptionListeAttente,
    ADS,
)
from mesads.fradm.tests.factories import PrefectureFactory, EPCIFactory, CommuneFactory


class ADSManagerAdministratorFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ADSManagerAdministrator

    prefecture = factory.SubFactory(PrefectureFactory)


class ADSManagerFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ADSManager

    administrator = factory.SubFactory(ADSManagerAdministratorFactory)

    class Params:
        for_prefecture = factory.Trait(
            content_object=factory.SubFactory(PrefectureFactory)
        )
        for_epci = factory.Trait(content_object=factory.SubFactory(EPCIFactory))
        for_commune = factory.Trait(content_object=factory.SubFactory(CommuneFactory))

    @factory.post_generation
    def for_object(self, create, extracted, **kwargs):
        """
        Permet d'appeler: ADSManagerFactory(for_object=une_instance)
        """
        if extracted is not None:
            self.content_object = extracted
            if create:
                self.save()


class ADSManagerRequestFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ADSManagerRequest

    ads_manager = factory.SubFactory(ADSManagerFactory)
    accepted = True


class ADSFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ADS

    ads_manager = factory.SubFactory(ADSManagerFactory)
    number = factory.Sequence(lambda n: f"{n + 1 }")
    ads_in_use = True


class InscriptionListeAttenteFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = InscriptionListeAttente

    nom = factory.Faker("last_name", locale="fr_FR")
    prenom = factory.Faker("first_name", locale="fr_FR")
    email = factory.Faker("email")
    adresse = factory.Faker("address", locale="fr_FR")

    numero = factory.Sequence(lambda n: f"{n + 1}")

    numero_licence = factory.Faker("bothify", text="LIC-########")
    numero_telephone = factory.Faker("phone_number", locale="fr_FR")

    date_depot_inscription = factory.LazyFunction(
        lambda: timezone.now().date() - timedelta(days=random.randint(30, 3 * 365))
    )

    status = InscriptionListeAttente.INSCRIT

    @factory.lazy_attribute
    def date_dernier_renouvellement(self):
        today = timezone.now().date()
        return today - timedelta(days=random.randint(1, 364))

    date_fin_validite = factory.LazyAttribute(
        lambda o: (
            o.date_dernier_renouvellement + relativedelta(years=1)
            if o.date_dernier_renouvellement
            else o.date_depot_inscription + relativedelta(years=1)
        )
    )

    class Params:
        # Inscription expirée : dernier renouvellement > 1 an
        expiree = factory.Trait(
            date_dernier_renouvellement=factory.LazyFunction(
                lambda: (
                    timezone.now().date() - timedelta(days=random.randint(366, 5 * 365))
                )
            )
        )

        # Inscription valide (déjà le comportement par défaut)
        valide = factory.Trait(
            date_dernier_renouvellement=factory.LazyFunction(
                lambda: (timezone.now().date() - timedelta(days=random.randint(1, 364)))
            )
        )
