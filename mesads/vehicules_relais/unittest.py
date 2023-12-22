from mesads.fradm.unittest import ClientTestCase as BaseClientTestCase

from mesads.vehicules_relais.models import Proprietaire


class ClientTestCase(BaseClientTestCase):
    def setUp(self):
        super().setUp()

        self.proprietaire_client, self.proprietaire_user = self.create_client()

        proprietaire = Proprietaire.objects.create(nom="Propriétaire")
        proprietaire.users.set([self.proprietaire_user])
