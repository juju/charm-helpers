import pkg_resources
import shutil
import tempfile
import unittest
import jinja2
import os.path
import pwd
import grp

import mock
from charmhelpers.core import templating


TEMPLATES_DIR = pkg_resources.resource_filename(__name__, 'templates')


class TestTemplating(unittest.TestCase):
    def setUp(self):
        self.charm_dir = pkg_resources.resource_filename(__name__, '')
        self._charm_dir_patch = mock.patch.object(templating.hookenv,
                                                  'charm_dir')
        self._charm_dir_mock = self._charm_dir_patch.start()
        self._charm_dir_mock.side_effect = lambda: self.charm_dir

    def tearDown(self):
        self._charm_dir_patch.stop()

    @mock.patch.object(templating.host.os, 'fchown')
    @mock.patch.object(templating.host, 'mkdir')
    @mock.patch.object(templating.host, 'log')
    def test_render(self, log, mkdir, fchown):
        with tempfile.NamedTemporaryFile() as fn1, \
                tempfile.NamedTemporaryFile() as fn2:
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
            templating.render('fake_cc.yml', fn1.name,
                              context, templates_dir=TEMPLATES_DIR)
            contents = open(fn1.name).read()
            self.assertRegexpMatches(contents, 'port: 1234')
            self.assertRegexpMatches(contents, 'host: example.com')
            self.assertRegexpMatches(contents, 'domain: api.foo.com')

            templating.render('test.conf', fn2.name, context,
                              templates_dir=TEMPLATES_DIR)
            contents = open(fn2.name).read()
            self.assertRegexpMatches(contents, 'listen 80')
            self.assertEqual(fchown.call_count, 2)
            # Not called, because the target directory exists. Calling
            # it would make the target directory world readable and
            # expose your secrets (!).
            self.assertEqual(mkdir.call_count, 0)

    @mock.patch.object(templating.host.os, 'fchown')
    @mock.patch.object(templating.host, 'mkdir')
    @mock.patch.object(templating.host, 'log')
    def test_render_from_string(self, log, mkdir, fchown):
        with tempfile.NamedTemporaryFile() as fn:
            context = {
                'foo': 'bar'
            }

            config_template = '{{ foo }}'
            templating.render('somefile.txt', fn.name,
                              context, templates_dir=TEMPLATES_DIR,
                              config_template=config_template)
            contents = open(fn.name).read()
            self.assertRegexpMatches(contents, 'bar')

            self.assertEqual(fchown.call_count, 1)
            # Not called, because the target directory exists. Calling
            # it would make the target directory world readable and
            # expose your secrets (!).
            self.assertEqual(mkdir.call_count, 0)

    @mock.patch.object(templating.host.os, 'fchown')
    @mock.patch.object(templating.host, 'mkdir')
    @mock.patch.object(templating.host, 'log')
    def test_render_loader(self, log, mkdir, fchown):
        with tempfile.NamedTemporaryFile() as fn1:
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
            template_loader = jinja2.ChoiceLoader([jinja2.FileSystemLoader(TEMPLATES_DIR)])
            templating.render('fake_cc.yml', fn1.name,
                              context, template_loader=template_loader)
            contents = open(fn1.name).read()
            self.assertRegexpMatches(contents, 'port: 1234')
            self.assertRegexpMatches(contents, 'host: example.com')
            self.assertRegexpMatches(contents, 'domain: api.foo.com')

    @mock.patch.object(templating.os.path, 'exists')
    @mock.patch.object(templating.host.os, 'fchown')
    @mock.patch.object(templating.host, 'mkdir')
    @mock.patch.object(templating.host, 'log')
    def test_render_no_dir(self, log, mkdir, fchown, exists):
        exists.return_value = False
        with tempfile.NamedTemporaryFile() as fn1, \
                tempfile.NamedTemporaryFile() as fn2:
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
            templating.render('fake_cc.yml', fn1.name,
                              context, templates_dir=TEMPLATES_DIR)
            contents = open(fn1.name).read()
            self.assertRegexpMatches(contents, 'port: 1234')
            self.assertRegexpMatches(contents, 'host: example.com')
            self.assertRegexpMatches(contents, 'domain: api.foo.com')

            templating.render('test.conf', fn2.name, context,
                              templates_dir=TEMPLATES_DIR)
            contents = open(fn2.name).read()
            self.assertRegexpMatches(contents, 'listen 80')
            self.assertEqual(fchown.call_count, 2)
            # Target directory was created, world readable (!).
            self.assertEqual(mkdir.call_count, 2)

    @mock.patch.object(templating.host.os, 'fchown')
    @mock.patch.object(templating.host, 'log')
    def test_render_2(self, log, fchown):
        tmpdir = tempfile.mkdtemp()
        fn1 = os.path.join(tmpdir, 'test.conf')
        try:
            context = {'nginx_port': 80}
            templating.render('test.conf', fn1, context,
                              owner=pwd.getpwuid(os.getuid()).pw_name,
                              group=grp.getgrgid(os.getgid()).gr_name,
                              templates_dir=TEMPLATES_DIR)
            with open(fn1) as f:
                contents = f.read()

            self.assertRegexpMatches(contents, 'something')
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    @mock.patch.object(templating, 'hookenv')
    @mock.patch('jinja2.Environment')
    def test_load_error(self, Env, hookenv):
        Env().get_template.side_effect = jinja2.exceptions.TemplateNotFound(
            'fake_cc.yml')
        self.assertRaises(
            jinja2.exceptions.TemplateNotFound, templating.render,
            'fake.src', 'fake.tgt', {}, templates_dir='tmpl')
        hookenv.log.assert_called_once_with(
            'Could not load template fake.src from tmpl.', level=hookenv.ERROR)
