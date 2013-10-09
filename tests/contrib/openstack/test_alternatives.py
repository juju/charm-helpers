from testtools import TestCase
from mock import patch

import charmhelpers.contrib.openstack.alternatives as alternatives


NAME = 'test'
SOURCE = '/var/lib/charm/test/test.conf'
TARGET = '/etc/test/test,conf'


class AlternativesTestCase(TestCase):

    @patch('subprocess.os.path')
    @patch('subprocess.check_call')
    def test_new_alternative(self, _check, _path):
        _path.exists.return_value = False
        alternatives.install_alternative(NAME,
                                         TARGET,
                                         SOURCE)
        _check.assert_called_with(
            ['update-alternatives', '--force', '--install',
             TARGET, NAME, SOURCE, '50']
        )

    @patch('subprocess.os.path')
    @patch('subprocess.check_call')
    def test_priority(self, _check, _path):
        _path.exists.return_value = False
        alternatives.install_alternative(NAME,
                                         TARGET,
                                         SOURCE, 100)
        _check.assert_called_with(
            ['update-alternatives', '--force', '--install',
             TARGET, NAME, SOURCE, '100']
        )

    @patch('os.unlink')
    @patch('shutil.move')
    @patch('subprocess.os.path')
    @patch('subprocess.check_call')
    def test_new_alternative_existing_file(self, _check,
                                           _path, _move,
                                           _unlink):
        _path.exists.return_value = True
        _path.isfile.return_value = True
        alternatives.install_alternative(NAME,
                                         TARGET,
                                         SOURCE)
        _check.assert_called_with(
            ['update-alternatives', '--force', '--install',
             TARGET, NAME, SOURCE, '50']
        )
        _move.assert_called_with(TARGET, '{}.bak'.format(TARGET))
        _unlink.assert_called_with(TARGET)

    @patch('os.unlink')
    @patch('shutil.move')
    @patch('subprocess.os.path')
    @patch('subprocess.check_call')
    def test_new_alternative_existing_dir(self, _check,
                                           _path, _move,
                                           _unlink):
        _path.exists.return_value = True
        _path.isfile.return_value = False
        _path.isdir.return_value = True
        alternatives.install_alternative(NAME,
                                         TARGET,
                                         SOURCE)
        _check.assert_called_with(
            ['update-alternatives', '--force', '--install',
             TARGET, NAME, SOURCE, '50']
        )
        _move.assert_called_with(TARGET, '{}.bak'.format(TARGET))
        _unlink.assert_called_with(TARGET)
