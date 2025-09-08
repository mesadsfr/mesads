from unittest.case import TestCase


from .selectattr import selectattr


class Object:
    key = "value"


class TestSelectAttr(TestCase):
    def test_selectattr(self):
        objects = [Object(), Object()]
        self.assertEqual(selectattr(objects, "key"), ["value", "value"])
