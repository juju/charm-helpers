import unittest
from mock import call, patch
import yaml

import tools.charm_helpers_sync.charm_helpers_sync as sync

import six
if not six.PY3:
    builtin_open = '__builtin__.open'
else:
    builtin_open = 'builtins.open'


INCLUDE = """
include:
    - core
    - contrib.openstack
    - contrib.storage
    - contrib.hahelpers:
        - utils
        - ceph_utils
        - cluster_utils
        - haproxy_utils
"""


class HelperSyncTests(unittest.TestCase):
    def test_clone_helpers(self):
        '''It properly branches the correct helpers branch'''
        with patch('subprocess.check_call') as check_call:
            sync.clone_helpers(work_dir='/tmp/foo', repo='git:charm-helpers')
            check_call.assert_called_with(['git',
                                           'clone', '--depth=1',
                                           'git:charm-helpers',
                                           '/tmp/foo/charm-helpers'])

    def test_module_path(self):
        '''It converts a python module path to a filesystem path'''
        self.assertEquals(sync._module_path('some.test.module'),
                          'some/test/module')

    def test_src_path(self):
        '''It renders the correct path to module within charm-helpers tree'''
        path = sync._src_path(src='/tmp/charm-helpers',
                              module='contrib.openstack')
        self.assertEquals('/tmp/charm-helpers/charmhelpers/contrib/openstack',
                          path)

    def test_dest_path(self):
        '''It correctly finds the correct install path within a charm'''
        path = sync._dest_path(dest='/tmp/mycharm/hooks/charmhelpers',
                               module='contrib.openstack')
        self.assertEquals('/tmp/mycharm/hooks/charmhelpers/contrib/openstack',
                          path)

    @patch(builtin_open)
    @patch('os.path.exists')
    @patch('os.walk')
    def test_ensure_init(self, walk, exists, _open):
        '''It ensures all subdirectories of a parent are python importable'''
        # os walk
        # os.path.join
        # os.path.exists
        # open
        def _walk(path):
            yield ('/tmp/hooks/', ['helpers'], [])
            yield ('/tmp/hooks/helpers', ['foo'], [])
            yield ('/tmp/hooks/helpers/foo', [], [])
        walk.side_effect = _walk
        exists.return_value = False
        sync.ensure_init('hooks/helpers/foo/')
        ex = [call('/tmp/hooks/__init__.py', 'wb'),
              call('/tmp/hooks/helpers/__init__.py', 'wb'),
              call('/tmp/hooks/helpers/foo/__init__.py', 'wb')]
        for c in ex:
            self.assertIn(c, _open.call_args_list)

    @patch('tools.charm_helpers_sync.charm_helpers_sync.ensure_init')
    @patch('os.path.isfile')
    @patch('shutil.copy')
    @patch('os.makedirs')
    @patch('os.path.exists')
    def test_sync_pyfile(self, exists, mkdirs, copy, isfile, ensure_init):
        '''It correctly syncs a py src file from src to dest'''
        exists.return_value = False
        isfile.return_value = True
        sync.sync_pyfile('/tmp/charm-helpers/core/host',
                         'hooks/charmhelpers/core')
        mkdirs.assert_called_with('hooks/charmhelpers/core')
        copy_f = call('/tmp/charm-helpers/core/host.py',
                      'hooks/charmhelpers/core')
        copy_i = call('/tmp/charm-helpers/core/__init__.py',
                      'hooks/charmhelpers/core')
        self.assertIn(copy_f, copy.call_args_list)
        self.assertIn(copy_i, copy.call_args_list)
        ensure_init.assert_called_with('hooks/charmhelpers/core')

    def _test_filter_dir(self, opts, isfile, isdir):
        '''It filters non-python files and non-module dirs from source'''
        files = {
            'bad_file.bin': 'f',
            'some_dir': 'd',
            'good_helper.py': 'f',
            'good_helper2.py': 'f',
            'good_helper3.py': 'f',
            'bad_file.img': 'f',
        }

        def _isfile(f):
            try:
                return files[f.split('/').pop()] == 'f'
            except KeyError:
                return False

        def _isdir(f):
            try:
                return files[f.split('/').pop()] == 'd'
            except KeyError:
                return False

        isfile.side_effect = _isfile
        isdir.side_effect = _isdir
        result = sync.get_filter(opts)(dir='/tmp/charm-helpers/core',
                                       ls=six.iterkeys(files))
        return result

    @patch('os.path.isdir')
    @patch('os.path.isfile')
    def test_filter_dir_no_opts(self, isfile, isdir):
        '''It filters out all non-py files by default'''
        result = self._test_filter_dir(opts=None, isfile=isfile, isdir=isdir)
        ex = ['bad_file.bin', 'bad_file.img', 'some_dir']
        self.assertEquals(sorted(ex), sorted(result))

    @patch('os.path.isdir')
    @patch('os.path.isfile')
    def test_filter_dir_with_include(self, isfile, isdir):
        '''It includes non-py files if specified as an include opt'''
        result = sorted(self._test_filter_dir(opts=['inc=*.img'],
                                              isfile=isfile, isdir=isdir))
        ex = sorted(['bad_file.bin', 'some_dir'])
        self.assertEquals(ex, result)

    @patch('os.path.isdir')
    @patch('os.path.isfile')
    def test_filter_dir_include_all(self, isfile, isdir):
        '''It does not filter anything if option specified to include all'''
        self.assertEquals(sync.get_filter(opts=['inc=*']), None)

    @patch('tools.charm_helpers_sync.charm_helpers_sync.get_filter')
    @patch('tools.charm_helpers_sync.charm_helpers_sync.ensure_init')
    @patch('shutil.copytree')
    @patch('shutil.rmtree')
    @patch('os.path.exists')
    def test_sync_directory(self, exists, rmtree, copytree, ensure_init,
                            _filter):
        '''It correctly syncs src directory to dest directory'''
        _filter.return_value = None
        sync.sync_directory('/tmp/charm-helpers/charmhelpers/core',
                            'hooks/charmhelpers/core')
        exists.return_value = True
        rmtree.assert_called_with('hooks/charmhelpers/core')
        copytree.assert_called_with('/tmp/charm-helpers/charmhelpers/core',
                                    'hooks/charmhelpers/core', ignore=None)
        ensure_init.assert_called_with('hooks/charmhelpers/core')

    @patch('os.path.isfile')
    def test_is_pyfile(self, isfile):
        '''It correctly identifies incomplete path to a py src file as such'''
        sync._is_pyfile('/tmp/charm-helpers/charmhelpers/core/host')
        isfile.assert_called_with(
            '/tmp/charm-helpers/charmhelpers/core/host.py'
        )

    @patch('tools.charm_helpers_sync.charm_helpers_sync.sync_pyfile')
    @patch('tools.charm_helpers_sync.charm_helpers_sync.sync_directory')
    @patch('os.path.isdir')
    def test_syncs_directory(self, is_dir, sync_dir, sync_pyfile):
        '''It correctly syncs a module directory'''
        is_dir.return_value = True
        sync.sync(src='/tmp/charm-helpers',
                  dest='hooks/charmhelpers',
                  module='contrib.openstack')

        sync_dir.assert_called_with(
            '/tmp/charm-helpers/charmhelpers/contrib/openstack',
            'hooks/charmhelpers/contrib/openstack', None)

        # __init__.py files leading to the directory were also synced.
        sync_pyfile.assert_has_calls([
            call('/tmp/charm-helpers/charmhelpers/__init__',
                 'hooks/charmhelpers'),
            call('/tmp/charm-helpers/charmhelpers/contrib/__init__',
                 'hooks/charmhelpers/contrib')])

    @patch('tools.charm_helpers_sync.charm_helpers_sync.sync_pyfile')
    @patch('tools.charm_helpers_sync.charm_helpers_sync._is_pyfile')
    @patch('os.path.isdir')
    def test_syncs_file(self, is_dir, is_pyfile, sync_pyfile):
        '''It correctly syncs a module file'''
        is_dir.return_value = False
        is_pyfile.return_value = True
        sync.sync(src='/tmp/charm-helpers',
                  dest='hooks/charmhelpers',
                  module='contrib.openstack.utils')
        sync_pyfile.assert_has_calls([
            call('/tmp/charm-helpers/charmhelpers/__init__',
                 'hooks/charmhelpers'),
            call('/tmp/charm-helpers/charmhelpers/contrib/__init__',
                 'hooks/charmhelpers/contrib'),
            call('/tmp/charm-helpers/charmhelpers/contrib/openstack/__init__',
                 'hooks/charmhelpers/contrib/openstack'),
            call('/tmp/charm-helpers/charmhelpers/contrib/openstack/utils',
                 'hooks/charmhelpers/contrib/openstack')])

    @patch('tools.charm_helpers_sync.charm_helpers_sync.sync')
    @patch('os.path.isdir')
    @patch('os.path.exists')
    def test_sync_helpers_from_config(self, exists, isdir, _sync):
        '''It correctly syncs a list of included helpers'''
        include = yaml.safe_load(INCLUDE)['include']
        isdir.return_value = True
        exists.return_value = False
        sync.sync_helpers(include=include,
                          src='/tmp/charm-helpers',

                          dest='hooks/charmhelpers')
        mods = [
            'core',
            'contrib.openstack',
            'contrib.storage',
            'contrib.hahelpers.utils',
            'contrib.hahelpers.ceph_utils',
            'contrib.hahelpers.cluster_utils',
            'contrib.hahelpers.haproxy_utils'
        ]

        ex_calls = []
        [ex_calls.append(
            call('/tmp/charm-helpers', 'hooks/charmhelpers', c, [])
        ) for c in mods]
        self.assertEquals(ex_calls, _sync.call_args_list)

    @patch('tools.charm_helpers_sync.charm_helpers_sync.sync')
    @patch('os.path.isdir')
    @patch('os.path.exists')
    @patch('shutil.rmtree')
    def test_sync_helpers_from_config_cleanup(self, _rmtree, _exists,
                                              isdir, _sync):
        '''It correctly syncs a list of included helpers'''
        include = yaml.safe_load(INCLUDE)['include']
        isdir.return_value = True
        _exists.return_value = True

        sync.sync_helpers(include=include,
                          src='/tmp/charm-helpers',

                          dest='hooks/charmhelpers')
        _rmtree.assert_called_with('hooks/charmhelpers')
        mods = [
            'core',
            'contrib.openstack',
            'contrib.storage',
            'contrib.hahelpers.utils',
            'contrib.hahelpers.ceph_utils',
            'contrib.hahelpers.cluster_utils',
            'contrib.hahelpers.haproxy_utils'
        ]

        ex_calls = []
        [ex_calls.append(
            call('/tmp/charm-helpers', 'hooks/charmhelpers', c, [])
        ) for c in mods]
        self.assertEquals(ex_calls, _sync.call_args_list)

    def test_extract_option_no_globals(self):
        '''It extracts option from an included item with no global options'''
        inc = 'contrib.openstack.templates|inc=*.template'
        result = sync.extract_options(inc)
        ex = ('contrib.openstack.templates', ['inc=*.template'])
        self.assertEquals(ex, result)

    def test_extract_option_with_global_as_string(self):
        '''It extracts option for include with global options as str'''
        inc = 'contrib.openstack.templates|inc=*.template'
        result = sync.extract_options(inc, global_options='inc=foo.*')
        ex = ('contrib.openstack.templates',
              ['inc=*.template', 'inc=foo.*'])
        self.assertEquals(ex, result)

    def test_extract_option_with_globals(self):
        '''It extracts option from an included item with global options'''
        inc = 'contrib.openstack.templates|inc=*.template'
        result = sync.extract_options(inc, global_options=['inc=*.cfg'])
        ex = ('contrib.openstack.templates', ['inc=*.template', 'inc=*.cfg'])
        self.assertEquals(ex, result)

    def test_extract_multiple_options_with_globals(self):
        '''It extracts multiple options from an included item'''
        inc = 'contrib.openstack.templates|inc=*.template,inc=foo.*'
        result = sync.extract_options(inc, global_options=['inc=*.cfg'])
        ex = ('contrib.openstack.templates',
              ['inc=*.template', 'inc=foo.*', 'inc=*.cfg'])
        self.assertEquals(ex, result)
