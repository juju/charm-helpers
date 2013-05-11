from testtools import TestCase
from mock import patch, call
import os
import shutil

from tempfile import mkdtemp

from charmhelpers.contrib.charmsupport import execd

class ExecDBaseTestCase(TestCase):
    def setUp(self):
        super(ExecDBaseTestCase, self).setUp()
        charm_dir = mkdtemp()
        self.test_charm_dir = charm_dir

        env_patcher = patch.dict('os.environ',
                                {'CHARM_DIR': self.test_charm_dir})
        env_patcher.start()
        self.addCleanup(env_patcher.stop)


    def cleanUp(self):
        shutil.rmtree(self.test_charm_dir)

class ExecDTestCase(ExecDBaseTestCase):

    def test_default_execd_dir(self):
        expected = os.path.join(self.test_charm_dir, 'exec.d')
        default_dir = execd.default_execd_dir()

        self.assertEqual(expected, default_dir)

    @patch('charmhelpers.contrib.charmsupport.execd.execd_run')
    def test_execd_preinstall_calls_charm_pre_install(self, mock_execd_run):
        execd_dir = 'testdir'
        execd.execd_preinstall(execd_dir)

        mock_execd_run.assert_called_with(execd_dir, 'charm-pre-install')


    @patch('charmhelpers.contrib.charmsupport.execd.default_execd_dir', return_value='foo')
    @patch('os.listdir', return_value=['a','b','c'])
    @patch('os.path.isdir', return_value=True)
    def test_execd_module_list_from_env(self, mock_isdir, mock_listdir,
                                        mock_defdir):
        module_names = ['a','b','c']
        mock_listdir.return_value = module_names

        modules = list(execd.execd_modules())

        expected = [os.path.join('foo', d) for d in module_names]
        self.assertEqual(modules, expected)

        mock_listdir.assert_called_with('foo')
        mock_isdir.assert_has_calls([call(d) for d in expected])


    @patch('charmhelpers.contrib.charmsupport.execd.default_execd_dir')
    @patch('os.listdir', return_value=['a','b','c'])
    @patch('os.path.isdir', return_value=True)
    def test_execd_module_list_with_dir(self, mock_isdir, mock_listdir,
                                        mock_defdir):
        module_names = ['a','b','c']
        mock_listdir.return_value = module_names

        modules = list(execd.execd_modules('foo'))

        expected = [os.path.join('foo', d) for d in module_names]
        self.assertEqual(modules, expected)
        self.assertFalse(mock_defdir.called)

        mock_listdir.assert_called_with('foo')
        mock_isdir.assert_has_calls([call(d) for d in expected])


    @patch('subprocess.check_call')
    @patch('charmhelpers.contrib.charmsupport.hookenv.log')
    @patch('os.path.isfile', return_value=True)
    @patch('os.access', return_value=True)
    @patch('charmhelpers.contrib.charmsupport.execd.execd_modules', return_value=['a','b'])
    def test_execd_run(self, mock_modules, mock_access, mock_isfile,
                       mock_log, mock_call):
        submodule = 'charm-foo'

        execd.execd_run(submodule)

        paths = [os.path.join(m, submodule) for m in ('a','b')]
        mock_call.assert_has_calls([call(d, shell=True) for d in paths])
