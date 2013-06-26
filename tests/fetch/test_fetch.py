from contextlib import contextmanager
from mock import patch, call, MagicMock
from testtools import TestCase
import yaml

import charmhelpers.fetch as fetch


@contextmanager
def patch_open():
    '''Patch open() to allow mocking both open() itself and the file that is
    yielded.

    Yields the mock for "open" and "file", respectively.'''
    mock_open = MagicMock(spec=open)
    mock_file = MagicMock(spec=file)

    @contextmanager
    def stub_open(*args, **kwargs):
        mock_open(*args, **kwargs)
        yield mock_file

    with patch('__builtin__.open', stub_open):
        yield mock_open, mock_file


class FetchTest(TestCase):
    @patch('subprocess.check_call')
    def test_add_source_ppa(self, check_call):
        source = "ppa:test-ppa"
        fetch.add_source(source=source)
        check_call.assert_called_with(['add-apt-repository',
                                       source])

    @patch('subprocess.check_call')
    def test_add_source_http(self, check_call):
        source = "http://archive.ubuntu.com/ubuntu raring-backports main"
        fetch.add_source(source=source)
        check_call.assert_called_with(['add-apt-repository',
                                       source])

    @patch.object(fetch, 'filter_installed_packages')
    @patch.object(fetch, 'apt_install')
    def test_add_source_cloud(self, apt_install, filter_pkg):
        source = "cloud:havana-updates"
        result = '''# Ubuntu Cloud Archive
deb http://ubuntu-cloud.archive.canonical.com/ubuntu havana-updates main
'''
        with patch_open() as (mock_open, mock_file):
            fetch.add_source(source=source)
            mock_file.write.assert_called_with(result)
        filter_pkg.assert_called_with(['ubuntu-cloud-keyring'])

    @patch('subprocess.check_call')
    def test_add_source_http_and_key(self, check_call):
        source = "http://archive.ubuntu.com/ubuntu raring-backports main"
        key = "akey"
        fetch.add_source(source=source, key=key)
        check_call.assert_has_calls([
              call(['add-apt-repository', source]),
              call(['apt-key', 'import', key])
        ])

    @patch.object(fetch, 'config')
    @patch.object(fetch, 'add_source')
    def test_configure_sources_single_source(self, add_source, config):
        config.side_effect = ['source', 'key']
        fetch.configure_sources()
        add_source.assert_called_with('source', 'key')

    @patch.object(fetch, 'config')
    @patch.object(fetch, 'add_source')
    def test_configure_sources_multiple_sources(self, add_source, config):
        sources = ["sourcea", "sourceb"]
        keys = ["keya", None]
        config.side_effect = [
            yaml.dump(sources),
            yaml.dump(keys)
        ]
        fetch.configure_sources()
        add_source.assert_has_calls([
            call('sourcea', 'keya'),
            call('sourceb', None)
        ])

    @patch.object(fetch, 'config')
    @patch.object(fetch, 'add_source')
    def test_configure_sources_missing_keys(self, add_source, config):
        sources = ["sourcea", "sourceb"]
        keys = ["keya"]  # Second key is missing
        config.side_effect = [
            yaml.dump(sources),
            yaml.dump(keys)
        ]
        self.assertRaises(fetch.SourceConfigError, fetch.configure_sources)

    @patch.object(fetch, 'apt_update')
    @patch.object(fetch, 'config')
    @patch.object(fetch, 'add_source')
    def test_configure_sources_apt_update_called(self, add_source, config,
                                                 apt_update):
        config.side_effect = ['source', 'key']
        fetch.configure_sources(update=True)
        add_source.assert_called_with('source', 'key')
        apt_update.assertCalled()
