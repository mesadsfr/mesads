import random
from datetime import timedelta

import factory
from dateutil.relativedelta import relativedelta
from django.contrib.contenttypes.models import ContentType
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from mesads.app.models import (
    ADS,
    ADSManager,
    ADSManagerAdministrator,
    ADSManagerDecree,
    ADSManagerRequest,
    InscriptionListeAttente,
)
from mesads.fradm.tests.factories import CommuneFactory, EPCIFactory, PrefectureFactory


class ADSManagerAdministratorFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ADSManagerAdministrator

    prefecture = factory.SubFactory(PrefectureFactory)


class ADSManagerFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ADSManager
        exclude = ("for_object",)

    administrator = factory.SubFactory(ADSManagerAdministratorFactory)

    class Params:
        for_object = None

        for_prefecture = factory.Trait(for_object=factory.SubFactory(PrefectureFactory))
        for_epci = factory.Trait(for_object=factory.SubFactory(EPCIFactory))
        for_commune = factory.Trait(for_object=factory.SubFactory(CommuneFactory))

    content_type = factory.LazyAttribute(
        lambda o: ContentType.objects.get_for_model(o.for_object)
        if o.for_object is not None
        else None
    )
    object_id = factory.LazyAttribute(
        lambda o: o.for_object.pk if o.for_object is not None else None
    )


class ADSManagerRequestFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ADSManagerRequest

    ads_manager = factory.SubFactory(ADSManagerFactory)
    accepted = True


class ADSManagerDecreeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ADSManagerDecree

    file = factory.LazyFunction(
        lambda: SimpleUploadedFile(
            "test.pdf", b"%PDF-1.4\n%Fake PDF\n", content_type="application/pdf"
        )
    )


class ADSFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ADS

    ads_manager = factory.SubFactory(ADSManagerFactory)
    number = factory.Sequence(lambda n: f"{n + 1}")
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
