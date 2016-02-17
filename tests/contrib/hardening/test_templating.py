from testtools import TestCase
from charmhelpers.contrib.hardening import templating


class TemplatingTestCase(TestCase):

    def setUp(self):
        super(TemplatingTestCase, self).setUp()

    def test_TemplateContext(self):
        ctxt = templating.TemplateContext('/some/file',
                                          {'contexts': []})
        self.assertEquals(ctxt.context, {})
        self.assertEquals(ctxt.service_actions, None)
        self.assertEquals(ctxt.post_hooks, None)
