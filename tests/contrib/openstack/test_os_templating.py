
import os
import unittest

from mock import patch, call, MagicMock

import charmhelpers.contrib.openstack.templating as templating

from jinja2.exceptions import TemplateNotFound

import six
if not six.PY3:
    builtin_open = '__builtin__.open'
else:
    builtin_open = 'builtins.open'


class FakeContextGenerator(object):
    interfaces = None

    def set(self, interfaces, context):
        self.interfaces = interfaces
        self.context = context

    def __call__(self):
        return self.context


class FakeLoader(object):
    def set(self, template):
        self.template = template

    def get(self, name):
        return self.template


class MockFSLoader(object):
    def __init__(self, dirs):
        self.searchpath = [dirs]


class MockChoiceLoader(object):
    def __init__(self, loaders):
        self.loaders = loaders


def MockTemplate():
    templ = MagicMock()
    templ.render = MagicMock()
    return templ


class TemplatingTests(unittest.TestCase):
    def setUp(self):
        path = os.path.dirname(__file__)
        self.loader = FakeLoader()
        self.context = FakeContextGenerator()

        self.addCleanup(patch.object(templating, 'apt_install').start().stop())
        self.addCleanup(patch.object(templating, 'log').start().stop())

        templating.FileSystemLoader = MockFSLoader
        templating.ChoiceLoader = MockChoiceLoader
        templating.Environment = MagicMock

        self.renderer = templating.OSConfigRenderer(templates_dir=path,
                                                    openstack_release='folsom')

    @patch.object(templating, 'apt_install')
    def test_initializing_a_render_ensures_jinja2_present(self, apt):
        '''Creatinga new renderer object installs jinja2 if needed'''
        # temp. undo the patching from setUp
        templating.FileSystemLoader = None
        templating.ChoiceLoader = None
        templating.Environment = None
        templating.OSConfigRenderer(templates_dir='/tmp',
                                    openstack_release='foo')
        templating.FileSystemLoader = MockFSLoader
        templating.ChoiceLoader = MockChoiceLoader
        templating.Environment = MagicMock
        if six.PY2:
            apt.assert_called_with('python-jinja2')
        else:
            apt.assert_called_with('python3-jinja2')

    def test_create_renderer_invalid_templates_dir(self):
        '''Ensure OSConfigRenderer checks templates_dir'''
        self.assertRaises(templating.OSConfigException,
                          templating.OSConfigRenderer,
                          templates_dir='/tmp/foooo0',
                          openstack_release='grizzly')

    def test_render_unregistered_config(self):
        '''Ensure cannot render an unregistered config file'''
        self.assertRaises(templating.OSConfigException,
                          self.renderer.render,
                          config_file='/tmp/foo')

    def test_write_unregistered_config(self):
        '''Ensure cannot write an unregistered config file'''
        self.assertRaises(templating.OSConfigException,
                          self.renderer.write,
                          config_file='/tmp/foo')

    def test_render_complete_context(self):
        '''It renders a template when provided a complete context'''
        self.loader.set('{{ foo }}')
        self.context.set(interfaces=['fooservice'], context={'foo': 'bar'})
        self.renderer.register('/tmp/foo', [self.context])
        with patch.object(self.renderer, '_get_template') as _get_t:
            fake_tmpl = MockTemplate()
            _get_t.return_value = fake_tmpl
            self.renderer.render('/tmp/foo')
            fake_tmpl.render.assert_called_with(self.context())
        self.assertIn('fooservice', self.renderer.complete_contexts())

    def test_render_incomplete_context_with_template(self):
        '''It renders a template when provided an incomplete context'''
        self.context.set(interfaces=['fooservice'], context={})
        self.renderer.register('/tmp/foo', [self.context])
        with patch.object(self.renderer, '_get_template') as _get_t:
            fake_tmpl = MockTemplate()
            _get_t.return_value = fake_tmpl
            self.renderer.render('/tmp/foo')
            fake_tmpl.render.assert_called_with({})
            self.assertNotIn('fooservice', self.renderer.complete_contexts())

    def test_render_template_registered_but_not_found(self):
        '''It loads a template by basename of config file first'''
        path = os.path.dirname(__file__)
        renderer = templating.OSConfigRenderer(templates_dir=path,
                                               openstack_release='folsom')
        e = TemplateNotFound('')
        renderer._get_template = MagicMock()
        renderer._get_template.side_effect = e
        renderer.register('/etc/nova/nova.conf', contexts=[])
        self.assertRaises(
            TemplateNotFound, renderer.render, '/etc/nova/nova.conf')

    def test_render_template_by_basename_first(self):
        '''It loads a template by basename of config file first'''
        path = os.path.dirname(__file__)
        renderer = templating.OSConfigRenderer(templates_dir=path,
                                               openstack_release='folsom')
        renderer._get_template = MagicMock()
        renderer.register('/etc/nova/nova.conf', contexts=[])
        renderer.render('/etc/nova/nova.conf')
        self.assertEquals(1, len(renderer._get_template.call_args_list))
        self.assertEquals(
            [call('nova.conf')], renderer._get_template.call_args_list)

    def test_render_template_by_munged_full_path_last(self):
        '''It loads a template by full path of config file second'''
        path = os.path.dirname(__file__)
        renderer = templating.OSConfigRenderer(templates_dir=path,
                                               openstack_release='folsom')
        tmp = MagicMock()
        tmp.render = MagicMock()
        e = TemplateNotFound('')
        renderer._get_template = MagicMock()
        renderer._get_template.side_effect = [e, tmp]
        renderer.register('/etc/nova/nova.conf', contexts=[])
        renderer.render('/etc/nova/nova.conf')
        self.assertEquals(2, len(renderer._get_template.call_args_list))
        self.assertEquals(
            [call('nova.conf'), call('etc_nova_nova.conf')],
            renderer._get_template.call_args_list)

    def test_render_template_by_basename(self):
        '''It renders template if it finds it by config file basename'''

    @patch(builtin_open)
    @patch.object(templating, 'get_loader')
    def test_write_out_config(self, loader, _open):
        '''It writes a templated config when provided a complete context'''
        self.context.set(interfaces=['fooservice'], context={'foo': 'bar'})
        self.renderer.register('/tmp/foo', [self.context])
        with patch.object(self.renderer, '_get_template') as _get_t:
            fake_tmpl = MockTemplate()
            _get_t.return_value = fake_tmpl
            self.renderer.write('/tmp/foo')
            _open.assert_called_with('/tmp/foo', 'wb')

    def test_write_all(self):
        '''It writes out all configuration files at once'''
        self.context.set(interfaces=['fooservice'], context={'foo': 'bar'})
        self.renderer.register('/tmp/foo', [self.context])
        self.renderer.register('/tmp/bar', [self.context])
        ex_calls = [
            call('/tmp/bar'),
            call('/tmp/foo'),
        ]
        with patch.object(self.renderer, 'write') as _write:
            self.renderer.write_all()
            self.assertEquals(sorted(ex_calls), sorted(_write.call_args_list))
            pass

    @patch.object(templating, 'get_loader')
    def test_reset_template_loader_for_new_os_release(self, loader):
        self.loader.set('')
        self.context.set(interfaces=['fooservice'], context={})
        loader.return_value = MockFSLoader('/tmp/foo')
        self.renderer.register('/tmp/foo', [self.context])
        self.renderer.render('/tmp/foo')
        loader.assert_called_with(os.path.dirname(__file__), 'folsom')
        self.renderer.set_release(openstack_release='grizzly')
        self.renderer.render('/tmp/foo')
        loader.assert_called_with(os.path.dirname(__file__), 'grizzly')

    @patch.object(templating, 'get_loader')
    def test_incomplete_context_not_reported_complete(self, loader):
        '''It does not recognize an incomplete context as a complete context'''
        self.context.set(interfaces=['fooservice'], context={})
        self.renderer.register('/tmp/foo', [self.context])
        self.assertNotIn('fooservice', self.renderer.complete_contexts())

    @patch.object(templating, 'get_loader')
    def test_complete_context_reported_complete(self, loader):
        '''It recognizes a complete context as a complete context'''
        self.context.set(interfaces=['fooservice'], context={'foo': 'bar'})
        self.renderer.register('/tmp/foo', [self.context])
        self.assertIn('fooservice', self.renderer.complete_contexts())

    @patch('os.path.isdir')
    def test_get_loader_no_templates_dir(self, isdir):
        '''Ensure getting loader fails with no template dir'''
        isdir.return_value = False
        self.assertRaises(templating.OSConfigException,
                          templating.get_loader,
                          templates_dir='/tmp/foo', os_release='foo')

    @patch('os.path.isdir')
    def test_get_loader_all_search_paths(self, isdir):
        '''Ensure loader reverse searches of all release template dirs'''
        isdir.return_value = True
        choice_loader = templating.get_loader('/tmp/foo',
                                              os_release='icehouse')
        dirs = [l.searchpath for l in choice_loader.loaders]

        common_tmplts = os.path.join(os.path.dirname(templating.__file__),
                                     'templates')
        expected = [['/tmp/foo/icehouse'],
                    ['/tmp/foo/havana'],
                    ['/tmp/foo/grizzly'],
                    ['/tmp/foo/folsom'],
                    ['/tmp/foo/essex'],
                    ['/tmp/foo/diablo'],
                    ['/tmp/foo'],
                    [common_tmplts]]
        self.assertEquals(dirs, expected)

    @patch('os.path.isdir')
    def test_get_loader_some_search_paths(self, isdir):
        '''Ensure loader reverse searches of some release template dirs'''
        isdir.return_value = True
        choice_loader = templating.get_loader('/tmp/foo', os_release='grizzly')
        dirs = [l.searchpath for l in choice_loader.loaders]

        common_tmplts = os.path.join(os.path.dirname(templating.__file__),
                                     'templates')

        expected = [['/tmp/foo/grizzly'],
                    ['/tmp/foo/folsom'],
                    ['/tmp/foo/essex'],
                    ['/tmp/foo/diablo'],
                    ['/tmp/foo'],
                    [common_tmplts]]
        self.assertEquals(dirs, expected)

    def test_register_template_with_list_of_contexts(self):
        '''Ensure registering a template with a list of context generators'''
        def _c1():
            pass

        def _c2():
            pass
        tmpl = templating.OSConfigTemplate(config_file='/tmp/foo',
                                           contexts=[_c1, _c2])
        self.assertEquals(tmpl.contexts, [_c1, _c2])

    def test_register_template_with_single_context(self):
        '''Ensure registering a template with a single non-list context'''
        def _c1():
            pass
        tmpl = templating.OSConfigTemplate(config_file='/tmp/foo',
                                           contexts=_c1)
        self.assertEquals(tmpl.contexts, [_c1])


class TemplatingStringTests(unittest.TestCase):
    def setUp(self):
        path = os.path.dirname(__file__)
        self.loader = FakeLoader()
        self.context = FakeContextGenerator()

        self.addCleanup(patch.object(templating,
                                     'apt_install').start().stop())
        self.addCleanup(patch.object(templating, 'log').start().stop())

        templating.FileSystemLoader = MockFSLoader
        templating.ChoiceLoader = MockChoiceLoader

        self.config_file = '/etc/confd/extensible.d/drop-in.conf'
        self.config_template = 'use: {{ fake_key }}'
        self.renderer = templating.OSConfigRenderer(templates_dir=path,
                                                    openstack_release='folsom')

    def test_render_template_from_string_full_context(self):
        '''
        Test rendering a specified config file with a string template
        and a context.
        '''

        context = {'fake_key': 'fake_val'}
        self.context.set(
            interfaces=['fooservice'],
            context=context
        )

        expected_output = 'use: {}'.format(context['fake_key'])

        self.renderer.register(
            config_file=self.config_file,
            contexts=[self.context],
            config_template=self.config_template
        )

        # should return a string given we render from an in-memory
        # template source
        output = self.renderer.render(self.config_file)

        self.assertEquals(output, expected_output)

    def test_render_template_from_string_incomplete_context(self):
        '''
        Test rendering a specified config file with a string template
        and a context.
        '''

        self.context.set(
            interfaces=['fooservice'],
            context={}
        )

        expected_output = 'use: '

        self.renderer.register(
            config_file=self.config_file,
            contexts=[self.context],
            config_template=self.config_template
        )

        # should return a string given we render from an in-memory
        # template source
        output = self.renderer.render(self.config_file)

        self.assertEquals(output, expected_output)

    def test_register_string_template_with_single_context(self):
        '''Template rendering from a provided string with a context'''
        def _c1():
            pass

        config_file = '/etc/confdir/custom-drop-in.conf'
        config_template = 'use: {{ key_available_in_c1 }}'
        tmpl = templating.OSConfigTemplate(
            config_file=config_file,
            contexts=_c1,
            config_template=config_template
        )

        self.assertEquals(tmpl.contexts, [_c1])
        self.assertEquals(tmpl.config_file, config_file)
        self.assertEquals(tmpl.config_template, config_template)
