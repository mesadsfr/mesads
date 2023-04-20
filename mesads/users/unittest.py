from dataclasses import dataclass
import random
import string

from django.test import Client, TestCase

from .models import User


class ClientTestCase(TestCase):
    def setUp(self):
        """Create the attributes:

        * anonymous_client: client not logged in
        * auth_client: client authenticated, but without permissions
        * auth_user: user object behind auth_client
        * admin_user: superuser
        """
        super().setUp()

        self.anonymous_client = Client()
        self.auth_client, self.auth_user = self.create_client()
        self.admin_client, self.admin_user = self.create_client(admin=True)

    def create_user(self, admin=False):
        email = "%s@domain.com" % "".join(
            random.choice(string.ascii_lowercase) for _ in range(16)
        )
        clear_password = "1234567890"

        if admin:
            user = User.objects.create_superuser(email=email, password=clear_password)
        else:
            user = User.objects.create_user(email=email, password=clear_password)

        @dataclass
        class Ret:
            obj: User
            clear_password: str

        return Ret(obj=user, clear_password=clear_password)

    def create_client(self, admin=False):
        user = self.create_user(admin=admin)

        client = Client()
        client.login(email=user.obj.email, password=user.clear_password)
        return (client, user.obj)
