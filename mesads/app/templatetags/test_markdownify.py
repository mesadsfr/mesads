from unittest.case import TestCase

from .markdownify import markdownify


class TestMarkdownify(TestCase):
    def test_markdownify(self):
        self.assertEqual(
            markdownify("**bold** statement"), "<p><strong>bold</strong> statement</p>"
        )
