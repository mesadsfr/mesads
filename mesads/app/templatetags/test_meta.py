from unittest.case import TestCase

from .meta import meta


class Object:
    class _meta:
        key = "value"


class TestMeta(TestCase):
    def test_meta(self):
        self.assertEqual(meta(Object(), "key"), "value")
