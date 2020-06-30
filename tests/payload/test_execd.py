from testtools import TestCase
from mock import patch
import os
import shutil
import stat

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

    def make_preinstall_executable(self, module_dir, execd_dir='exec.d',
                                   error_on_preinstall=False):
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
        with open(charm_pre_install_path, 'w+') as f:
            if not error_on_preinstall:
                f.write("#!/bin/bash\n"
                        "/usr/bin/touch {}".format(pre_install_success_path))
            else:
                f.write("#!/bin/bash\n"
                        "echo stdout_from_pre_install\n"
                        "echo stderr_from_pre_install >&2\n"
                        "exit 1")

        # ensure it is executable.
        perms = stat.S_IRUSR + stat.S_IXUSR
        os.chmod(charm_pre_install_path, perms)

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

    def test_execd_module_list_from_env(self):
        modules = ['basenode', 'mod2', 'c']
        for module in modules:
            self.make_preinstall_executable(module_dir=module)

        actual_mod_paths = list(execd.execd_module_paths())

        expected_mod_paths = [
            os.path.join(self.test_charm_dir, 'exec.d', module)
            for module in modules]
        self.assertSetEqual(set(actual_mod_paths), set(expected_mod_paths))

    def test_execd_module_list_with_dir(self):
        modules = ['basenode', 'mod2', 'c']
        for module in modules:
            self.make_preinstall_executable(module_dir=module,
                                            execd_dir='foo')

        actual_mod_paths = list(execd.execd_module_paths(
            execd_dir=os.path.join(self.test_charm_dir, 'foo')))

        expected_mod_paths = [
            os.path.join(self.test_charm_dir, 'foo', module)
            for module in modules]
        self.assertSetEqual(set(actual_mod_paths), set(expected_mod_paths))

    def test_execd_module_paths_no_execd_dir(self):
        """Empty list is returned when the exec.d doesn't exist."""
        actual_mod_paths = list(execd.execd_module_paths())

        self.assertEqual(actual_mod_paths, [])

    def test_execd_submodule_list(self):
        modules = ['basenode', 'mod2', 'c']
        for module in modules:
            self.make_preinstall_executable(module_dir=module)

        submodules = list(execd.execd_submodule_paths('charm-pre-install'))

        expected = [os.path.join(self.test_charm_dir, 'exec.d', mod,
                                 'charm-pre-install') for mod in modules]
        self.assertEqual(sorted(submodules), sorted(expected))

    def test_execd_run(self):
        modules = ['basenode', 'mod2', 'c']
        for module in modules:
            self.make_preinstall_executable(module_dir=module)

        execd.execd_run('charm-pre-install')

        self.assert_preinstall_called_for_mod('basenode')
        self.assert_preinstall_called_for_mod('mod2')
        self.assert_preinstall_called_for_mod('c')

    @patch('charmhelpers.core.hookenv.log')
    def test_execd_run_logs_exception(self, log_):
        self.make_preinstall_executable(module_dir='basenode',
                                        error_on_preinstall=True)

        execd.execd_run('charm-pre-install', die_on_error=False)

        expected_log = ('Error (1) running  {}/exec.d/basenode/'
                        'charm-pre-install. Output: '
                        'stdout_from_pre_install\n'
                        'stderr_from_pre_install\n'.format(self.test_charm_dir))
        log_.assert_called_with(expected_log)

    @patch('charmhelpers.core.hookenv.log')
    @patch('sys.exit')
    def test_execd_run_dies_with_return_code(self, exit_, log):
        self.make_preinstall_executable(module_dir='basenode',
                                        error_on_preinstall=True)

        with open(os.devnull, 'wb') as devnull:
            execd.execd_run('charm-pre-install', stderr=devnull)

        exit_.assert_called_with(1)
