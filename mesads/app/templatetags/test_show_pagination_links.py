from django.core.paginator import Paginator
from django.test import TestCase


from .show_pagination_links import show_pagination_links


class TestShowPaginationLinks(TestCase):
    def test_inclusion_tag(self):
        # 100 items, but only one page
        paginator = Paginator(range(100), 100)
        ret = show_pagination_links(paginator.get_page(1))
        self.assertEqual(ret, {})

        # 100 items, 2 per page
        paginator = Paginator(range(100), 2)

        # First page
        ret = show_pagination_links(paginator.get_page(1))
        self.assertEqual(len(ret['pages']), 6)
        self.assertFalse(ret['pages'][0].is_first)
        self.assertFalse(ret['pages'][1].is_prev)
        self.assertTrue(ret['pages'][-2].is_next)
        self.assertTrue(ret['pages'][-1].is_last)

        # Middle page
        ret = show_pagination_links(paginator.get_page(10))
        self.assertEqual(len(ret['pages']), 10)
        self.assertTrue(ret['pages'][0].is_first)
        self.assertTrue(ret['pages'][1].is_prev)
        self.assertTrue(ret['pages'][-2].is_next)
        self.assertTrue(ret['pages'][-1].is_last)

        # Last page
        ret = show_pagination_links(paginator.get_page(50))
        self.assertEqual(len(ret['pages']), 5)
        self.assertTrue(ret['pages'][0].is_first)
        self.assertTrue(ret['pages'][1].is_prev)
        self.assertFalse(ret['pages'][-2].is_next)
        self.assertFalse(ret['pages'][-1].is_last)
