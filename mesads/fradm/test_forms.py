from .forms import FrenchAdministrationForm
from .unittest import ClientTestCase


class TestFrenchAdministrationForm(ClientTestCase):
    def test_ok(self):
        form = FrenchAdministrationForm(data={
            'prefecture': self.fixtures_prefectures[0].id
        })
        self.assertTrue(form.is_valid())

    def test_clean_no_selection(self):
        form = FrenchAdministrationForm(data={})
        self.assertFalse(form.is_valid())

    def test_clean_too_many_selections(self):
        form = FrenchAdministrationForm(data={
            'prefecture': self.fixtures_prefectures[0].id,
            'epci': self.fixtures_epci[0].id
        })
        self.assertFalse(form.is_valid())
