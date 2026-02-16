import pytest
from django.test import Client

from mesads.app.tests.factories import ADSManagerFactory, ADSManagerRequestFactory
from mesads.users.tests.factories import UserFactory


@pytest.fixture
def user():
    return UserFactory()


@pytest.fixture
def user_factory():
    def _user_factory(**kwargs):
        return UserFactory(**kwargs)

    return _user_factory


@pytest.fixture
def client():
    return Client()


@pytest.fixture
def client_logged(user):
    client = Client()
    client.force_login(user=user)
    return client


@pytest.fixture
def client_factory(user):
    def _client_factory(user_=None):
        client = Client()
        client.force_login(user=user_ or user)
        return client

    return _client_factory


@pytest.fixture
def commune():
    return ADSManagerFactory(for_commune=True)


@pytest.fixture
def ads_manager_request(user, commune):
    def _ads_manager_request(user_=None, manager_=None, **kwargs):
        return ADSManagerRequestFactory(
            user=user_ or user, ads_manager=manager_ or commune
        )

    return _ads_manager_request
