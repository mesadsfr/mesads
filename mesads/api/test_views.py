from mesads.app.unittest import ClientTestCase

from .views import ADSUpdatesViewSet


class TestADSUpdatesViewSet(ClientTestCase):
    def test_get_queryset(self):
        queryset = ADSUpdatesViewSet().get_queryset()
        print(queryset)