import random
import string

from django.test import Client, TestCase

from .models import User


class ClientTestCase(TestCase):
    def setUp(self):
        """Create the attributes:

        * anonymous_client: client not logged in
        * auth_client: client authenticated, but without permissions
        """
        super().setUp()

        self.anonymous_client = Client()
        self.auth_client, _ = self.create_client()

    def create_client(self):
        email = '%s@domain.com' % ''.join(random.choice(string.ascii_lowercase) for _ in range(16))
        clear_password = '1234567890'

        user = User.objects.create_user(email=email, password=clear_password)

        client = Client()
        client.login(email=user.email, password=clear_password)
        return (client, user)
