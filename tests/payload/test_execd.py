from testtools import TestCase
from mock import patch
import os
import shutil
import stat
from subprocess import CalledProcessError

from tempfile import mkdtemp

from charmhelpers.payload import execd

class ExecDTestCase(TestCase):

    def setUp(self):
        super(ExecDTestCase, self).setUp()
        charm_dir = mkdtemp()
        self.addCleanup(shutil.rmtree, charm_dir)
        self.test_charm_dir = charm_dir

        env_patcher = patch.dict('os.environ',
                                {'CHARM_DIR': self.test_charm_dir})
        env_patcher.start()
        self.addCleanup(env_patcher.stop)

    def test_default_execd_dir(self):
        expected = os.path.join(self.test_charm_dir, 'exec.d')
        default_dir = execd.default_execd_dir()

        self.assertEqual(expected, default_dir)

    def make_preinstall_executable(self, module_dir, execd_dir='exec.d'):
        """Add a charm-pre-install to module dir.
        
        When executed, the charm-pre-install will create a second
        file in the same directory, charm-pre-install-success.
        """
        module_path = os.path.join(self.test_charm_dir, execd_dir, module_dir) 
        os.makedirs(module_path)

        charm_pre_install_path = os.path.join(module_path,
                                              'charm-pre-install')
        pre_install_success_path = os.path.join(module_path,
                                                'charm-pre-install-success')
        with open(charm_pre_install_path, 'w+') as fd:
            fd.write("#!/bin/bash\n"
                     "/usr/bin/touch {}".format(pre_install_success_path))
        os.chmod(charm_pre_install_path, stat.S_IXUSR | stat.S_IRUSR)

    def assert_preinstall_called_for_mod(self, module_dir,
                                         execd_dir='exec.d'):
        """Asserts that the charm-pre-install-success file exists."""
        expected_file = os.path.join(self.test_charm_dir, execd_dir,
                                     module_dir, 'charm-pre-install-success')
        files = os.listdir(os.path.dirname(expected_file))
        self.assertTrue(os.path.exists(expected_file), "files were: %s. charmdir is: %s" % (files, self.test_charm_dir))

    def test_execd_preinstall(self):
        """All charm-pre-install hooks are executed."""
        self.make_preinstall_executable(module_dir='basenode')
        self.make_preinstall_executable(module_dir='mod2')

        execd.execd_preinstall()

        self.assert_preinstall_called_for_mod('basenode')
        self.assert_preinstall_called_for_mod('mod2')

    @patch('charmhelpers.payload.execd.execd_run')
    def test_execd_preinstall_calls_charm_pre_install(self, mock_execd_run):
        execd_dir = 'testdir'
        execd.execd_preinstall(execd_dir)

        mock_execd_run.assert_called_with(execd_dir, 'charm-pre-install')


    @patch('charmhelpers.payload.execd.default_execd_dir')
    @patch('os.listdir')
    @patch('os.path.isdir')
    def test_execd_module_list_from_env(self, mock_isdir, mock_listdir,
                                        mock_defdir):
        mock_isdir.return_value = True
        mock_defdir.return_value = 'foo'
        module_names = ['a','b','c']
        mock_listdir.return_value = module_names

        modules = list(execd.execd_module_paths())

        expected = [os.path.join('foo', d) for d in module_names]
        self.assertEqual(modules, expected)

        mock_listdir.assert_called_with('foo')
        mock_isdir.assert_has_calls([call(d) for d in expected])


    @patch('charmhelpers.payload.execd.default_execd_dir')
    @patch('os.listdir')
    @patch('os.path.isdir')
    def test_execd_module_list_with_dir(self, mock_isdir, mock_listdir,
                                        mock_defdir):
        mock_isdir.return_value = True
        module_names = ['a','b','c']
        mock_listdir.return_value = module_names

        modules = list(execd.execd_module_paths('foo'))

        expected = [os.path.join('foo', d) for d in module_names]
        self.assertEqual(modules, expected)
        self.assertFalse(mock_defdir.called)

        mock_listdir.assert_called_with('foo')
        mock_isdir.assert_has_calls([call(d) for d in expected])


    @patch('os.path.isfile')
    @patch('os.access')
    @patch('charmhelpers.payload.execd.execd_module_paths')
    def test_execd_submodule_list(self, modlist_, access_, isfile_):
        isfile_.return_value = True
        access_.return_value = True
        module_list = ['a','b','c']
        modlist_.return_value = module_list
        submodules = [s for s in execd.execd_submodule_paths('sm')]

        expected = [os.path.join(d, 'sm') for d in module_list]
        self.assertEqual(submodules, expected)


    @patch('subprocess.check_call')
    @patch('charmhelpers.payload.execd.execd_submodule_paths')
    def test_execd_run(self, submods_, call_):
        submod_list = ['a','b','c']
        submods_.return_value = submod_list
        execd.execd_run('foo')

        submods_.assert_called_with('foo', None)
        call_.assert_has_calls([call(d, shell=True) for d in submod_list])


    @patch('subprocess.check_call')
    @patch('charmhelpers.payload.execd.execd_submodule_paths')
    @patch('charmhelpers.core.hookenv.log')
    def test_execd_run_logs_exception(self, log_, submods_, check_call_):
        submod_list = ['a','b','c']
        submods_.return_value = submod_list
        err_msg = 'darn'
        check_call_.side_effect = CalledProcessError(1, 'cmd', err_msg)

        execd.execd_run('foo')
        log_.assert_called_with(err_msg)


    @patch('subprocess.check_call')
    @patch('charmhelpers.payload.execd.execd_submodule_paths')
    @patch('charmhelpers.core.hookenv.log')
    @patch('sys.exit')
    def test_execd_run_dies_with_return_code(self, exit_, log_, submods_,
                                             check_call_):
        submod_list = ['a','b','c']
        submods_.return_value = submod_list
        retcode = 9
        check_call_.side_effect = CalledProcessError(retcode, 'cmd')

        execd.execd_run('foo', die_on_error=True)
        exit_.assert_called_with(retcode)
