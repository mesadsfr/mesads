from unittest.case import TestCase

from mesads.app.templatetags.markdownify import markdownify


class TestMarkdownify(TestCase):
    def test_markdownify(self):
        self.assertEqual(
            markdownify("**bold** statement"), "<p><strong>bold</strong> statement</p>"
        )
