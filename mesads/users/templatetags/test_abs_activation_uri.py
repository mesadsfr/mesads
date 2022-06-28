from django.test import TestCase, RequestFactory
from django.template import Context

from .abs_activation_uri import abs_activation_uri


class TestTemplateTag(TestCase):
    def test_abs_activation_uri(self):
        factory = RequestFactory()
        request = factory.get('/')

        context = Context({
            'request': request,
        })
        ret = abs_activation_uri(context, 'the_activation_key')
        self.assertEqual(ret, 'http://testserver/auth/activate/the_activation_key/')
