import subprocess
import os

from tests.helpers import patch_open
from testtools import TestCase
from mock import (
    patch,
    MagicMock,
    call,
)
from charmhelpers.fetch import centos as fetch


def getenv(update=None):
    # return a copy of os.environ with update applied.
    # this was necessary because some modules modify os.environment directly
    copy = os.environ.copy()
    if update is not None:
        copy.update(update)
    return copy


class FetchTest(TestCase):

    @patch("charmhelpers.fetch.log")
    @patch('yum.YumBase.doPackageLists')
    def test_filter_packages_missing_centos(self, yumBase, log):

        class MockPackage:
            def __init__(self, name):
                self.base_package_name = name

        yum_dict = {
            'installed': {
                MockPackage('vim')
            },
            'available': {
                MockPackage('vim')
            }
        }
        import yum
        yum.YumBase.return_value.doPackageLists.return_value = yum_dict
        result = fetch.filter_installed_packages(['vim', 'emacs'])
        self.assertEquals(result, ['emacs'])

    @patch("charmhelpers.fetch.log")
    def test_filter_packages_none_missing_centos(self, log):

        class MockPackage:
            def __init__(self, name):
                self.base_package_name = name

        yum_dict = {
            'installed': {
                MockPackage('vim')
            },
            'available': {
                MockPackage('vim')
            }
        }
        import yum
        yum.yumBase.return_value.doPackageLists.return_value = yum_dict
        result = fetch.filter_installed_packages(['vim'])
        self.assertEquals(result, [])

    @patch('charmhelpers.fetch.centos.log')
    @patch('yum.YumBase.doPackageLists')
    def test_filter_packages_not_available_centos(self, yumBase, log):

        class MockPackage:
            def __init__(self, name):
                self.base_package_name = name

        yum_dict = {
            'installed': {
                MockPackage('vim')
            }
        }
        import yum
        yum.YumBase.return_value.doPackageLists.return_value = yum_dict

        result = fetch.filter_installed_packages(['vim', 'joe'])
        self.assertEquals(result, ['joe'])

    @patch('charmhelpers.fetch.centos.log')
    def test_add_source_none_centos(self, log):
        fetch.add_source(source=None)
        self.assertTrue(log.called)

    @patch('charmhelpers.fetch.centos.log')
    @patch('os.listdir')
    def test_add_source_http_centos(self, listdir, log):
        source = "http://archive.ubuntu.com/ubuntu raring-backports main"
        with patch_open() as (mock_open, mock_file):
            fetch.add_source(source=source)
            listdir.assert_called_with('/etc/yum.repos.d/')
            mock_file.write.assert_has_calls([
                call("[archive.ubuntu.com_ubuntu raring-backports main]\n"),
                call("name=archive.ubuntu.com/ubuntu raring-backports main\n"),
                call("baseurl=http://archive.ubuntu.com/ubuntu raring"
                     "-backports main\n\n")])

    @patch('charmhelpers.fetch.centos.log')
    @patch('os.listdir')
    @patch('subprocess.check_call')
    def test_add_source_http_and_key_id_centos(self, check_call,
                                               listdir, log):
        source = "http://archive.ubuntu.com/ubuntu raring-backports main"
        key_id = "akey"
        with patch_open() as (mock_open, mock_file):
            fetch.add_source(source=source, key=key_id)
            listdir.assert_called_with('/etc/yum.repos.d/')
            mock_file.write.assert_has_calls([
                call("[archive.ubuntu.com_ubuntu raring-backports main]\n"),
                call("name=archive.ubuntu.com/ubuntu raring-backports main\n"),
                call("baseurl=http://archive.ubuntu.com/ubuntu raring"
                     "-backports main\n\n")])
        check_call.assert_called_with(['rpm', '--import', key_id])

    @patch('charmhelpers.fetch.centos.log')
    @patch('os.listdir')
    @patch('subprocess.check_call')
    def test_add_source_https_and_key_id_centos(self, check_call,
                                                listdir, log):
        source = "https://USER:PASS@private-ppa.launchpad.net/project/awesome"
        key_id = "GPGPGP"
        with patch_open() as (mock_open, mock_file):
            fetch.add_source(source=source, key=key_id)
            listdir.assert_called_with('/etc/yum.repos.d/')
            mock_file.write.assert_has_calls([
                call("[_USER:PASS@private-ppa.launchpad"
                     ".net_project_awesome]\n"),
                call("name=/USER:PASS@private-ppa.launchpad.net"
                     "/project/awesome\n"),
                call("baseurl=https://USER:PASS@private-ppa.launchpad.net"
                     "/project/awesome\n\n")])
        check_call.assert_called_with(['rpm', '--import', key_id])

    @patch('charmhelpers.fetch.centos.log')
    @patch.object(fetch, 'NamedTemporaryFile')
    @patch('os.listdir')
    @patch('subprocess.check_call')
    def test_add_source_http_and_key_centos(self, check_call,
                                            listdir, temp_file, log):
        source = "http://archive.ubuntu.com/ubuntu raring-backports main"
        key = '''
            -----BEGIN PGP PUBLIC KEY BLOCK-----
            [...]
            -----END PGP PUBLIC KEY BLOCK-----
            '''
        file_mock = MagicMock()
        file_mock.name = 'temporary_file'
        temp_file.return_value.__enter__.return_value = file_mock
        listdir.return_value = []

        with patch_open() as (mock_open, mock_file):
            fetch.add_source(source=source, key=key)
            listdir.assert_called_with('/etc/yum.repos.d/')
            self.assertTrue(log.called)
        check_call.assert_called_with(['rpm', '--import', file_mock.name])
        file_mock.write.assert_called_once_with(key)
        file_mock.flush.assert_called_once_with()
        file_mock.seek.assert_called_once_with(0)


class YumTests(TestCase):

    @patch('subprocess.call')
    @patch('charmhelpers.fetch.centos.log')
    def test_yum_upgrade_non_fatal(self, log, mock_call):
        options = ['--foo', '--bar']
        fetch.upgrade(options)

        mock_call.assert_called_with(['yum', '--assumeyes',
                                      '--foo', '--bar', 'upgrade'],
                                     env=getenv())

    @patch('subprocess.check_call')
    @patch('charmhelpers.fetch.centos.log')
    def test_yum_upgrade_fatal(self, log, mock_call):
        options = ['--foo', '--bar']
        fetch.upgrade(options, fatal=True)

        mock_call.assert_called_with(['yum', '--assumeyes',
                                      '--foo', '--bar', 'upgrade'],
                                     env=getenv())

    @patch('subprocess.call')
    @patch('charmhelpers.fetch.centos.log')
    def test_installs_yum_packages(self, log, mock_call):
        packages = ['foo', 'bar']
        options = ['--foo', '--bar']

        fetch.install(packages, options)

        mock_call.assert_called_with(['yum', '--assumeyes',
                                      '--foo', '--bar', 'install',
                                      'foo', 'bar'],
                                     env=getenv())

    @patch('subprocess.call')
    @patch('charmhelpers.fetch.centos.log')
    def test_installs_yum_packages_without_options(self, log, mock_call):
        packages = ['foo', 'bar']
        fetch.install(packages)

        mock_call.assert_called_with(['yum', '--assumeyes',
                                      'install', 'foo', 'bar'],
                                     env=getenv())

    @patch('subprocess.call')
    @patch('charmhelpers.fetch.centos.log')
    def test_installs_yum_packages_as_string(self, log, mock_call):
        packages = 'foo bar'
        fetch.install(packages)

        mock_call.assert_called_with(['yum', '--assumeyes',
                                      'install', 'foo bar'],
                                     env=getenv())

    @patch('subprocess.check_call')
    @patch('charmhelpers.fetch.centos.log')
    def test_installs_yum_packages_with_possible_errors(self, log, mock_call):
        packages = ['foo', 'bar']
        options = ['--foo', '--bar']

        fetch.install(packages, options, fatal=True)

        mock_call.assert_called_with(['yum', '--assumeyes',
                                      '--foo', '--bar',
                                      'install', 'foo', 'bar'],
                                     env=getenv())

    @patch('subprocess.check_call')
    @patch('charmhelpers.fetch.centos.log')
    def test_purges_yum_packages_as_string_fatal(self, log, mock_call):
        packages = 'irrelevant names'
        mock_call.side_effect = OSError('fail')

        self.assertRaises(OSError, fetch.purge, packages, fatal=True)
        self.assertTrue(log.called)

    @patch('subprocess.check_call')
    @patch('charmhelpers.fetch.centos.log')
    def test_purges_yum_packages_fatal(self, log, mock_call):
        packages = ['irrelevant', 'names']
        mock_call.side_effect = OSError('fail')

        self.assertRaises(OSError, fetch.purge, packages, fatal=True)
        self.assertTrue(log.called)

    @patch('subprocess.call')
    @patch('charmhelpers.fetch.centos.log')
    def test_purges_yum_packages_as_string_nofatal(self, log, mock_call):
        packages = 'foo bar'
        fetch.purge(packages)

        self.assertTrue(log.called)
        mock_call.assert_called_with(['yum', '--assumeyes',
                                      'remove', 'foo bar'],
                                     env=getenv())

    @patch('subprocess.call')
    @patch('charmhelpers.fetch.centos.log')
    def test_purges_yum_packages_nofatal(self, log, mock_call):
        packages = ['foo', 'bar']
        fetch.purge(packages)

        self.assertTrue(log.called)
        mock_call.assert_called_with(['yum', '--assumeyes',
                                      'remove', 'foo', 'bar'],
                                     env=getenv())

    @patch('subprocess.check_call')
    @patch('charmhelpers.fetch.centos.log')
    def test_yum_update_fatal(self, log, check_call):
        fetch.update(fatal=True)
        check_call.assert_called_with(['yum', '--assumeyes', 'update'],
                                      env=getenv())
        self.assertTrue(log.called)

    @patch('subprocess.check_output')
    @patch('charmhelpers.fetch.centos.log')
    def test_yum_search(self, log, check_output):
        package = ['irrelevant']

        from charmhelpers.fetch.centos import yum_search
        yum_search(package)
        check_output.assert_called_with(['yum', 'search', 'irrelevant'])
        self.assertTrue(log.called)

    @patch('subprocess.check_call')
    @patch('time.sleep')
    def test_run_yum_command_retries_if_fatal(self, check_call, sleep):
        """The _run_yum_command function retries the command if it can't get
        the YUM lock."""
        self.called = False

        def side_effect(*args, **kwargs):
            """
            First, raise an exception (can't acquire lock), then return 0
            (the lock is grabbed).
            """
            if not self.called:
                self.called = True
                raise subprocess.CalledProcessError(
                    returncode=1, cmd="some command")
            else:
                return 0

        check_call.side_effect = side_effect
        check_call.return_value = 0
        from charmhelpers.fetch.centos import _run_yum_command
        _run_yum_command(["some", "command"], fatal=True)
        self.assertTrue(sleep.called)
