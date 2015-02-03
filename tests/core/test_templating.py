import os
import pkg_resources
import tempfile
import unittest
import jinja2

import mock
from charmhelpers.core import templating


TEMPLATES_DIR = pkg_resources.resource_filename(__name__, 'templates')


class TestTemplating(unittest.TestCase):
    def setUp(self):
        self.charm_dir = pkg_resources.resource_filename(__name__, '')
        self._charm_dir_patch = mock.patch.object(templating.hookenv, 'charm_dir')
        self._charm_dir_mock = self._charm_dir_patch.start()
        self._charm_dir_mock.side_effect = lambda: self.charm_dir

    def tearDown(self):
        self._charm_dir_patch.stop()

    @mock.patch.object(templating.host.os, 'fchown')
    @mock.patch.object(templating.host, 'mkdir')
    @mock.patch.object(templating.host, 'log')
    def test_render(self, log, mkdir, fchown):
        _, fn1 = tempfile.mkstemp()
        _, fn2 = tempfile.mkstemp()
        try:
            context = {
                'nats': {
                    'port': '1234',
                    'host': 'example.com',
                },
                'router': {
                    'domain': 'api.foo.com'
                },
                'nginx_port': 80,
            }
            templating.render('fake_cc.yml', fn1,
                              context, templates_dir=TEMPLATES_DIR)
            contents = open(fn1).read()
            self.assertRegexpMatches(contents, 'port: 1234')
            self.assertRegexpMatches(contents, 'host: example.com')
            self.assertRegexpMatches(contents, 'domain: api.foo.com')

            templating.render('test.conf', fn2, context,
                              templates_dir=TEMPLATES_DIR)
            contents = open(fn2).read()
            self.assertRegexpMatches(contents, 'listen 80')
            self.assertEqual(fchown.call_count, 2)
            self.assertEqual(mkdir.call_count, 2)
        finally:
            for fn in (fn1, fn2):
                if os.path.exists(fn):
                    os.remove(fn)

    @mock.patch.object(templating, 'hookenv')
    @mock.patch('jinja2.Environment')
    def test_load_error(self, Env, hookenv):
        Env().get_template.side_effect = jinja2.exceptions.TemplateNotFound('fake_cc.yml')
        self.assertRaises(
            jinja2.exceptions.TemplateNotFound, templating.render,
            'fake.src', 'fake.tgt', {}, templates_dir='tmpl')
        hookenv.log.assert_called_once_with('Could not load template fake.src from tmpl.', level=hookenv.ERROR)
