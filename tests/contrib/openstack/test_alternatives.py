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

    @patch('shutil.move')
    @patch('subprocess.os.path')
    @patch('subprocess.check_call')
    def test_new_alternative_existing_file(self, _check,
                                           _path, _move):
        _path.exists.return_value = True
        _path.islink.return_value = False
        alternatives.install_alternative(NAME,
                                         TARGET,
                                         SOURCE)
        _check.assert_called_with(
            ['update-alternatives', '--force', '--install',
             TARGET, NAME, SOURCE, '50']
        )
        _move.assert_called_with(TARGET, '{}.bak'.format(TARGET))

    @patch('shutil.move')
    @patch('subprocess.os.path')
    @patch('subprocess.check_call')
    def test_new_alternative_existing_link(self, _check,
                                           _path, _move):
        _path.exists.return_value = True
        _path.islink.return_value = True
        alternatives.install_alternative(NAME,
                                         TARGET,
                                         SOURCE)
        _check.assert_called_with(
            ['update-alternatives', '--force', '--install',
             TARGET, NAME, SOURCE, '50']
        )
        _move.assert_not_called()

    @patch('subprocess.check_call')
    def test_remove_alternative(self, _check):
        alternatives.remove_alternative(NAME, SOURCE)
        _check.assert_called_with(
            ['update-alternatives', '--remove',
             NAME, SOURCE]
        )
