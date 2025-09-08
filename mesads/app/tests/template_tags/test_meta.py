from unittest.case import TestCase

from mesads.app.templatetags.meta import meta


class Object:
    class _meta:
        key = "value"


class TestMeta(TestCase):
    def test_meta(self):
        self.assertEqual(meta(Object(), "key"), "value")
