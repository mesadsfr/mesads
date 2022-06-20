from django.test import Client, TestCase

from .models import User


class ClientTestCase(TestCase):
    def setUp(self):
        self.anonymous_client = Client()

        User.objects.create_user(email='user@domain.com', password='123')
        self.auth_client = Client()
        self.auth_client.login(email='user@domain.com', password='123')
