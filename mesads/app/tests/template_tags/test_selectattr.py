from unittest.case import TestCase


from mesads.app.templatetags.selectattr import selectattr


class Object:
    key = "value"


class TestSelectAttr(TestCase):
    def test_selectattr(self):
        objects = [Object(), Object()]
        self.assertEqual(selectattr(objects, "key"), ["value", "value"])
