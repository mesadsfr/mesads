from datetime import date
from unittest.case import TestCase


from mesads.app.templatetags.str_to_date import str_to_date


class TestStrToDate(TestCase):
    def test_str_to_date(self):
        today = date.today()
        self.assertIs(str_to_date(today), today)
        self.assertEqual(str_to_date(today.strftime("%Y-%m-%d")), today)
