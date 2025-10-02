import factory

from mesads.fradm.models import Prefecture, EPCI, Commune


class PrefectureFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Prefecture

    numero = factory.Sequence(lambda n: "{:02d}".format(n + 1))
    libelle = factory.Sequence(lambda n: f"Département du {'{:02d}'.format(n + 1)}")


class EPCIFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = EPCI


class CommuneFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Commune

    insee = factory.Sequence(lambda n: "{:08d}".format(n + 1))
