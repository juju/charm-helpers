import mock
import six
import subprocess
import unittest

from tests.helpers import patch_open, mock_open

import charmhelpers.contrib.openstack.ssh_migrations as ssh_migrations

if not six.PY3:
    builtin_open = '__builtin__.open'
    builtin_import = '__builtin__.__import__'
else:
    builtin_open = 'builtins.open'
    builtin_import = 'builtins.__import__'


UNIT1_HOST_KEY_1 = """|1|EaIiWNsBsaSke5T5bdDlaV5xKPU=|WKMu3Va+oNwRjXmPGOZ+mrpWbM8= ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDZdZdR7I35ymFdspruN1CIez/0m62sJeld2nLuOGaNbdl/rk5bGrWUAZh6c9p9H53FAqGAXBD/1C8dZ5dgIAGdTs7PAZq7owXCpgUPQcGOYVAtBwv8qfnWyI1W+Vpi6vnb2sgYr6XGbB9b84i4vrd98IIpXIleC9qd0VUTSYgd7+NPaFNoK0HZmqcNEf5leaa8sgSf4t5F+BTWEXzU3ql/3isFT8lEpJ9N8wOvNzAoFEQcxqauvOJn72QQ6kUrQT3NdQFUMHquS/s+nBrQNPbUmzqrvSOed75Qk8359zqU1Rce7U39cqc0scYi1ak3oJdojwfLFKJw4TMPn/Pq7JnT"""
UNIT1_HOST_KEY_2 = """|1|mCyYWqJl8loqV6LCY84lu2rpqLA=|51m+M+0ES3jYVzr3Kco3CDg8hEY= ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDZdZdR7I35ymFdspruN1CIez/0m62sJeld2nLuOGaNbdl/rk5bGrWUAZh6c9p9H53FAqGAXBD/1C8dZ5dgIAGdTs7PAZq7owXCpgUPQcGOYVAtBwv8qfnWyI1W+Vpi6vnb2sgYr6XGbB9b84i4vrd98IIpXIleC9qd0VUTSYgd7+NPaFNoK0HZmqcNEf5leaa8sgSf4t5F+BTWEXzU3ql/3isFT8lEpJ9N8wOvNzAoFEQcxqauvOJn72QQ6kUrQT3NdQFUMHquS/s+nBrQNPbUmzqrvSOed75Qk8359zqU1Rce7U39cqc0scYi1ak3oJdojwfLFKJw4TMPn/Pq7JnT"""
UNIT2_HOST_KEY_1 = """|1|eWagMqrN7XmX7NdVpZbqMZ2cb4Q=|3jgGiFEU9SMhXwdX0w0kkG54CZc= ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC27Lv4wtAiPIOTsrUCFOU4qaNsov+LZSVHtxlu0aERuD+oU3ZILXOITXJlDohweXN6YuP4hFg49FF119gmMag+hDiA8/BztQmsplkwHrWEPuWKpReLRNLBU+Nt78jrJkjTK8Egwxbaxu8fAPZkCgGyeLkIH4ghrdWlOaWYXzwuxXkYWSpQOgF6E/T+19JKVKNpt2i6w7q9vVwZEjwVr30ubs1bNdPzE9ylNLQRrGa7c38SKsEos5RtZJjEuZGTC9KI0QdEgwnxxNMlT/CIgwWA1V38vLsosF2pHKxbmtCNvBuPNtrBDgXhukVqyEh825RhTAyQYGshMCbAbxl/M9c3"""
UNIT2_HOST_KEY_2 = """|1|zRH8troNwhVzrkMx86E5Ibevw5s=|gESlgkwUumP8q0A6l+CoRlFRpTw= ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC27Lv4wtAiPIOTsrUCFOU4qaNsov+LZSVHtxlu0aERuD+oU3ZILXOITXJlDohweXN6YuP4hFg49FF119gmMag+hDiA8/BztQmsplkwHrWEPuWKpReLRNLBU+Nt78jrJkjTK8Egwxbaxu8fAPZkCgGyeLkIH4ghrdWlOaWYXzwuxXkYWSpQOgF6E/T+19JKVKNpt2i6w7q9vVwZEjwVr30ubs1bNdPzE9ylNLQRrGa7c38SKsEos5RtZJjEuZGTC9KI0QdEgwnxxNMlT/CIgwWA1V38vLsosF2pHKxbmtCNvBuPNtrBDgXhukVqyEh825RhTAyQYGshMCbAbxl/M9c3"""
HOST_KEYS = [UNIT1_HOST_KEY_1, UNIT1_HOST_KEY_2,
             UNIT2_HOST_KEY_1, UNIT2_HOST_KEY_2]
UNIT1_PUBKEY_1 = """ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDqtnB3zh3sMufZd1khi44su0hTg/LqLb3ma2iyueTULZikDYa65UidVxzsa6r0Y9jkHwknGlh7fNnGdmc3S8EE+rVUNF4r3JF2Zd/pdfCBia/BmKJcO7+NyRWc8ihlrA3xYUSm+Yg8ZIpqoSb1LKjgAdYISh9HQQaXut2sXtHESdpilNpDf42AZfuQM+B0op0v7bq86ZXOM1rvdJriI6BduHaAOux+d9HDNvV5AxYTICrUkXqIvdHnoRyOFfhTcKun0EtuUxpDiAi0im9C+i+MPwMvA6AmRbot6Tqt2xZPRBYY8+WF7I5cBoovES/dWKP5TZwaGBr+WNv+z2JJhvlN root@juju-4665be-20180716142533-8"""
UNIT2_PUBKEY_1 = """ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCkWfkVrG7wTnfifvL0GkmDj6L33PKrWjzN2hOwZb9EoxwNzFGTMTBIpepTAnO6hdFBwtus1Ej/L12K6L/0YRDZAKjE7yTWOsh1kUxPZ1INRCqLILiefE5A/LPNx8NDb+d/2ryc5QmOQXUALs6mC5VDNchImUp9L7l0RIzPOgPXZCqMC1nZLqqX+eI9EUaf29/+NztYw59rFAa3hWNe8RJCSFeU+iWirWP8rfX9jsLzD9hO3nuZjP23M6tv1jX9LQD+8qkx0WSMa2WrIjkMiclP6tkyCJOZogyoPzZm/+dUhLeY9bIizbZCQKH/b4gOl5m/PkWoqEFshfqGzUIPkAJp root@juju-4665be-20180716142533-9"""
PUB_KEYS = [UNIT1_PUBKEY_1, UNIT2_PUBKEY_1]


class SSHMigrationsTests(unittest.TestCase):

    def setUp(self):
        self._patches = {}
        self._patches_start = {}

    def tearDown(self):
        """Run teardown of patches."""
        for k, v in self._patches.items():
            v.stop()
            setattr(self, k, None)
        self._patches = None
        self._patches_start = None

    def patch_object(self, obj, attr, return_value=None, name=None, new=None,
                     **kwargs):
        """Patch the given object."""
        if name is None:
            name = attr
        if new is not None:
            mocked = mock.patch.object(obj, attr, new=new, **kwargs)
        else:
            mocked = mock.patch.object(obj, attr, **kwargs)
        self._patches[name] = mocked
        started = mocked.start()
        if new is None:
            started.return_value = return_value
        self._patches_start[name] = started
        setattr(self, name, started)

    def setup_mocks_ssh_directory_for_unit(self, app_name, ssh_dir_exists,
                                           app_dir_exists, auth_keys_exists,
                                           known_hosts_exists, user=None):
        def _isdir(x):
            return {
                ssh_dir + '/': ssh_dir_exists,
                app_dir: app_dir_exists}[x]

        def _isfile(x):
            return {
                '{}/authorized_keys'.format(app_dir): auth_keys_exists,
                '{}/known_hosts'.format(app_dir): known_hosts_exists}[x]

        if user:
            app_name = "{}_{}".format(app_name, user)
        ssh_dir = '/etc/nova/compute_ssh'
        app_dir = '{}/{}'.format(ssh_dir, app_name)

        self.patch_object(ssh_migrations.os, 'mkdir')
        self.patch_object(ssh_migrations.os.path, 'isdir', side_effect=_isdir)
        self.patch_object(ssh_migrations.os.path, 'isfile',
                          side_effect=_isfile)

    def test_ssh_directory_for_unit(self):
        self.setup_mocks_ssh_directory_for_unit(
            'nova-compute-lxd',
            ssh_dir_exists=True,
            app_dir_exists=True,
            auth_keys_exists=True,
            known_hosts_exists=True)
        self.assertEqual(
            ssh_migrations.ssh_directory_for_unit('nova-compute-lxd'),
            '/etc/nova/compute_ssh/nova-compute-lxd')
        self.assertFalse(self.mkdir.called)

    def test_ssh_directory_for_unit_user(self):
        self.setup_mocks_ssh_directory_for_unit(
            'nova-compute-lxd',
            ssh_dir_exists=True,
            app_dir_exists=True,
            auth_keys_exists=True,
            known_hosts_exists=True,
            user='nova')
        self.assertEqual(
            ssh_migrations.ssh_directory_for_unit(
                'nova-compute-lxd',
                user='nova'),
            '/etc/nova/compute_ssh/nova-compute-lxd_nova')
        self.assertFalse(self.mkdir.called)

    def test_ssh_directory_missing_dir(self):
        self.setup_mocks_ssh_directory_for_unit(
            'nova-compute-lxd',
            ssh_dir_exists=False,
            app_dir_exists=True,
            auth_keys_exists=True,
            known_hosts_exists=True)
        self.assertEqual(
            ssh_migrations.ssh_directory_for_unit('nova-compute-lxd'),
            '/etc/nova/compute_ssh/nova-compute-lxd')
        self.mkdir.assert_called_once_with('/etc/nova/compute_ssh/')

    def test_ssh_directory_missing_dirs(self):
        self.setup_mocks_ssh_directory_for_unit(
            'nova-compute-lxd',
            ssh_dir_exists=False,
            app_dir_exists=False,
            auth_keys_exists=True,
            known_hosts_exists=True)
        self.assertEqual(
            ssh_migrations.ssh_directory_for_unit('nova-compute-lxd'),
            '/etc/nova/compute_ssh/nova-compute-lxd')
        mkdir_calls = [
            mock.call('/etc/nova/compute_ssh/'),
            mock.call('/etc/nova/compute_ssh/nova-compute-lxd')]
        self.mkdir.assert_has_calls(mkdir_calls)

    @mock.patch(builtin_open)
    def test_ssh_directory_missing_file(self, _open):
        self.setup_mocks_ssh_directory_for_unit(
            'nova-compute-lxd',
            ssh_dir_exists=True,
            app_dir_exists=True,
            auth_keys_exists=False,
            known_hosts_exists=True)
        self.assertEqual(
            ssh_migrations.ssh_directory_for_unit('nova-compute-lxd'),
            '/etc/nova/compute_ssh/nova-compute-lxd')
        _open.assert_called_once_with(
            '/etc/nova/compute_ssh/nova-compute-lxd/authorized_keys',
            'w')
        self.assertFalse(self.mkdir.called)

    @mock.patch(builtin_open)
    def test_ssh_directory_missing_files(self, _open):
        self.setup_mocks_ssh_directory_for_unit(
            'nova-compute-lxd',
            ssh_dir_exists=True,
            app_dir_exists=True,
            auth_keys_exists=False,
            known_hosts_exists=False)
        self.assertEqual(
            ssh_migrations.ssh_directory_for_unit('nova-compute-lxd'),
            '/etc/nova/compute_ssh/nova-compute-lxd')
        open_calls = [
            mock.call(
                '/etc/nova/compute_ssh/nova-compute-lxd/authorized_keys',
                'w'),
            mock.call().close(),
            mock.call(
                '/etc/nova/compute_ssh/nova-compute-lxd/known_hosts',
                'w'),
            mock.call().close()]
        _open.assert_has_calls(open_calls)
        self.assertFalse(self.mkdir.called)

    def setup_ssh_directory_for_unit_mocks(self):
        self.patch_object(
            ssh_migrations,
            'ssh_directory_for_unit',
            return_value='/somedir')

    def test_known_hosts(self):
        self.setup_ssh_directory_for_unit_mocks()
        self.assertEqual(
            ssh_migrations.known_hosts('nova-compute-lxd'),
            '/somedir/known_hosts')

    def test_authorized_keys(self):
        self.setup_ssh_directory_for_unit_mocks()
        self.assertEqual(
            ssh_migrations.authorized_keys('nova-compute-lxd'),
            '/somedir/authorized_keys')

    @mock.patch('subprocess.check_output')
    def test_ssh_known_host_key(self, _check_output):
        self.setup_ssh_directory_for_unit_mocks()
        _check_output.return_value = UNIT1_HOST_KEY_1
        self.assertEqual(
            ssh_migrations.ssh_known_host_key(
                'juju-4665be-20180716142533-8',
                'nova-compute-lxd'),
            UNIT1_HOST_KEY_1)

    @mock.patch('subprocess.check_output')
    def test_ssh_known_host_key_multi_match(self, _check_output):
        self.setup_ssh_directory_for_unit_mocks()
        _check_output.return_value = '{}\n{}\n'.format(UNIT1_HOST_KEY_1,
                                                       UNIT1_HOST_KEY_2)
        self.assertEqual(
            ssh_migrations.ssh_known_host_key(
                'juju-4665be-20180716142533-8',
                'nova-compute-lxd'),
            UNIT1_HOST_KEY_1)

    @mock.patch('subprocess.check_output')
    def test_ssh_known_host_key_rc1(self, _check_output):
        self.setup_ssh_directory_for_unit_mocks()
        _check_output.side_effect = subprocess.CalledProcessError(
            cmd=['anything'],
            returncode=1,
            output=UNIT1_HOST_KEY_1)
        self.assertEqual(
            ssh_migrations.ssh_known_host_key(
                'juju-4665be-20180716142533-8',
                'nova-compute-lxd'),
            UNIT1_HOST_KEY_1)

    @mock.patch('subprocess.check_output')
    def test_ssh_known_host_key_rc2(self, _check_output):
        self.setup_ssh_directory_for_unit_mocks()
        _check_output.side_effect = subprocess.CalledProcessError(
            cmd=['anything'],
            returncode=2,
            output='')
        with self.assertRaises(subprocess.CalledProcessError):
            ssh_migrations.ssh_known_host_key(
                'juju-4665be-20180716142533-8',
                'nova-compute-lxd')

    @mock.patch('subprocess.check_output')
    def test_ssh_known_host_key_no_match(self, _check_output):
        self.setup_ssh_directory_for_unit_mocks()
        _check_output.return_value = ''
        self.assertIsNone(
            ssh_migrations.ssh_known_host_key(
                'juju-4665be-20180716142533-8',
                'nova-compute-lxd'))

    @mock.patch('subprocess.check_call')
    def test_remove_known_host(self, _check_call):
        self.patch_object(ssh_migrations, 'log')
        self.setup_ssh_directory_for_unit_mocks()
        ssh_migrations.remove_known_host(
            'juju-4665be-20180716142533-8',
            'nova-compute-lxd')
        _check_call.assert_called_once_with([
            'ssh-keygen',
            '-f',
            '/somedir/known_hosts',
            '-R',
            'juju-4665be-20180716142533-8'])

    def test_is_same_key(self):
        self.assertTrue(
            ssh_migrations.is_same_key(UNIT1_HOST_KEY_1, UNIT1_HOST_KEY_2))

    def test_is_same_key_false(self):
        self.assertFalse(
            ssh_migrations.is_same_key(UNIT1_HOST_KEY_1, UNIT2_HOST_KEY_1))

    def setup_mocks_add_known_host(self):
        self.setup_ssh_directory_for_unit_mocks()
        self.patch_object(ssh_migrations.subprocess, 'check_output')
        self.patch_object(ssh_migrations, 'log')
        self.patch_object(ssh_migrations, 'ssh_known_host_key')
        self.patch_object(ssh_migrations, 'remove_known_host')

    def test_add_known_host(self):
        self.setup_mocks_add_known_host()
        self.check_output.return_value = UNIT1_HOST_KEY_1
        self.ssh_known_host_key.return_value = ''
        with patch_open() as (mock_open, mock_file):
            ssh_migrations.add_known_host(
                'juju-4665be-20180716142533-8',
                'nova-compute-lxd')
            mock_file.write.assert_called_with(UNIT1_HOST_KEY_1 + '\n')
            mock_open.assert_called_with('/somedir/known_hosts', 'a')
        self.assertFalse(self.remove_known_host.called)

    def test_add_known_host_existing_invalid_key(self):
        self.setup_mocks_add_known_host()
        self.check_output.return_value = UNIT1_HOST_KEY_1
        self.ssh_known_host_key.return_value = UNIT2_HOST_KEY_1
        with patch_open() as (mock_open, mock_file):
            ssh_migrations.add_known_host(
                'juju-4665be-20180716142533-8',
                'nova-compute-lxd')
            mock_file.write.assert_called_with(UNIT1_HOST_KEY_1 + '\n')
            mock_open.assert_called_with('/somedir/known_hosts', 'a')
        self.remove_known_host.assert_called_once_wth(
            'juju-4665be-20180716142533-8',
            'nova-compute-lxd')

    def test_add_known_host_existing_valid_key(self):
        self.setup_mocks_add_known_host()
        self.check_output.return_value = UNIT2_HOST_KEY_1
        self.ssh_known_host_key.return_value = UNIT2_HOST_KEY_1
        with patch_open() as (mock_open, mock_file):
            ssh_migrations.add_known_host(
                'juju-4665be-20180716142533-8',
                'nova-compute-lxd')
            self.assertFalse(mock_open.called)
        self.assertFalse(self.remove_known_host.called)

    def test_ssh_authorized_key_exists(self):
        self.setup_mocks_add_known_host()
        contents = '{}\n{}\n'.format(UNIT1_PUBKEY_1, UNIT2_PUBKEY_1)
        with mock_open('/somedir/authorized_keys', contents=contents):
            self.assertTrue(
                ssh_migrations.ssh_authorized_key_exists(
                    UNIT1_PUBKEY_1,
                    'nova-compute-lxd'))

    def test_ssh_authorized_key_exists_false(self):
        self.setup_mocks_add_known_host()
        contents = '{}\n'.format(UNIT1_PUBKEY_1)
        with mock_open('/somedir/authorized_keys', contents=contents):
            self.assertFalse(
                ssh_migrations.ssh_authorized_key_exists(
                    UNIT2_PUBKEY_1,
                    'nova-compute-lxd'))

    def test_add_authorized_key(self):
        self.setup_mocks_add_known_host()
        with patch_open() as (mock_open, mock_file):
            ssh_migrations.add_authorized_key(
                UNIT1_PUBKEY_1,
                'nova-compute-lxd')
            mock_file.write.assert_called_with(UNIT1_PUBKEY_1 + '\n')
            mock_open.assert_called_with('/somedir/authorized_keys', 'a')

    def setup_mocks_ssh_compute_add_host_and_key(self):
        self.setup_ssh_directory_for_unit_mocks()
        self.patch_object(ssh_migrations, 'log')
        self.patch_object(ssh_migrations, 'get_hostname')
        self.patch_object(ssh_migrations, 'get_host_ip')
        self.patch_object(ssh_migrations, 'ns_query')
        self.patch_object(ssh_migrations, 'add_known_host')
        self.patch_object(ssh_migrations, 'ssh_authorized_key_exists')
        self.patch_object(ssh_migrations, 'add_authorized_key')

    def test_ssh_compute_add_host_and_key(self):
        self.setup_mocks_ssh_compute_add_host_and_key()
        self.get_hostname.return_value = 'alt-hostname.project.serverstack'
        self.ns_query.return_value = '10.6.0.17'
        ssh_migrations.ssh_compute_add_host_and_key(
            UNIT1_PUBKEY_1,
            'juju-4665be-20180716142533-8.project.serverstack',
            '10.5.0.17',
            'nova-compute-lxd')
        expect_hosts = [
            'juju-4665be-20180716142533-8.project.serverstack',
            'alt-hostname.project.serverstack',
            'alt-hostname']
        add_known_host_calls = []
        for host in expect_hosts:
            add_known_host_calls.append(
                mock.call(host, 'nova-compute-lxd', None))
        self.add_known_host.assert_has_calls(
            add_known_host_calls,
            any_order=True)
        self.add_authorized_key.assert_called_once_with(
            UNIT1_PUBKEY_1,
            'nova-compute-lxd',
            None)

    def test_ssh_compute_add_host_and_key_priv_addr_not_ip(self):
        self.setup_mocks_ssh_compute_add_host_and_key()
        self.get_hostname.return_value = 'alt-hostname.project.serverstack'
        self.ns_query.return_value = '10.6.0.17'
        self.get_host_ip.return_value = '10.6.0.17'
        ssh_migrations.ssh_compute_add_host_and_key(
            UNIT1_PUBKEY_1,
            'juju-4665be-20180716142533-8.project.serverstack',
            'bob.maas',
            'nova-compute-lxd')
        expect_hosts = [
            'bob.maas',
            'juju-4665be-20180716142533-8.project.serverstack',
            '10.6.0.17',
            'bob']
        add_known_host_calls = []
        for host in expect_hosts:
            add_known_host_calls.append(
                mock.call(host, 'nova-compute-lxd', None))
        self.add_known_host.assert_has_calls(
            add_known_host_calls,
            any_order=True)
        self.add_authorized_key.assert_called_once_with(
            UNIT1_PUBKEY_1,
            'nova-compute-lxd',
            None)

    def test_ssh_compute_add_host_and_key_ipv6(self):
        self.setup_mocks_ssh_compute_add_host_and_key()
        ssh_migrations.ssh_compute_add_host_and_key(
            UNIT1_PUBKEY_1,
            'juju-4665be-20180716142533-8.project.serverstack',
            'fe80::8842:a9ff:fe53:72e4',
            'nova-compute-lxd')
        self.add_known_host.assert_called_once_with(
            'fe80::8842:a9ff:fe53:72e4',
            'nova-compute-lxd',
            None)
        self.add_authorized_key.assert_called_once_with(
            UNIT1_PUBKEY_1,
            'nova-compute-lxd',
            None)

    @mock.patch.object(ssh_migrations, 'ssh_compute_add_host_and_key')
    @mock.patch.object(ssh_migrations, 'relation_get')
    def test_ssh_compute_add(self, _relation_get,
                             _ssh_compute_add_host_and_key):
        _relation_get.return_value = {
            'hostname': 'juju-4665be-20180716142533-8.project.serverstack',
            'private-address': '10.5.0.17',
        }
        ssh_migrations.ssh_compute_add(
            UNIT1_PUBKEY_1,
            'nova-compute-lxd',
            rid='cloud-compute:23',
            unit='nova-compute-lxd/2')
        _ssh_compute_add_host_and_key.assert_called_once_with(
            UNIT1_PUBKEY_1,
            'juju-4665be-20180716142533-8.project.serverstack',
            '10.5.0.17',
            'nova-compute-lxd',
            user=None)

    @mock.patch.object(ssh_migrations, 'known_hosts')
    def test_ssh_known_hosts_lines(self, _known_hosts):
        _known_hosts.return_value = '/somedir/known_hosts'
        contents = '\n'.join(HOST_KEYS)
        with mock_open('/somedir/known_hosts', contents=contents):
            self.assertEqual(
                ssh_migrations.ssh_known_hosts_lines('nova-compute-lxd'),
                HOST_KEYS)

    @mock.patch.object(ssh_migrations, 'authorized_keys')
    def test_ssh_authorized_keys_lines(self, _authorized_keys):
        _authorized_keys.return_value = '/somedir/authorized_keys'
        contents = '\n'.join(PUB_KEYS)
        with mock_open('/somedir/authorized_keys', contents=contents):
            self.assertEqual(
                ssh_migrations.ssh_authorized_keys_lines('nova-compute-lxd'),
                PUB_KEYS)

    def setup_mocks_ssh_compute_remove(self, isfile, authorized_keys_lines):
        self.patch_object(
            ssh_migrations,
            'ssh_authorized_keys_lines',
            return_value=authorized_keys_lines)
        self.patch_object(ssh_migrations, 'known_hosts')
        self.patch_object(
            ssh_migrations,
            'authorized_keys',
            return_value='/somedir/authorized_keys')
        self.patch_object(
            ssh_migrations.os.path,
            'isfile',
            return_value=isfile)

    def test_ssh_compute_remove(self):
        self.setup_mocks_ssh_compute_remove(
            isfile=True,
            authorized_keys_lines=PUB_KEYS)
        with patch_open() as (mock_open, mock_file):
            ssh_migrations.ssh_compute_remove(
                UNIT1_PUBKEY_1,
                'nova-compute-lxd')
            mock_file.write.assert_called_with(UNIT2_PUBKEY_1 + '\n')
            mock_open.assert_called_with('/somedir/authorized_keys', 'w')

    def test_ssh_compute_remove_missing_file(self):
        self.setup_mocks_ssh_compute_remove(
            isfile=False,
            authorized_keys_lines=PUB_KEYS)
        with patch_open() as (mock_open, mock_file):
            ssh_migrations.ssh_compute_remove(
                UNIT1_PUBKEY_1,
                'nova-compute-lxd')
            self.assertFalse(mock_file.write.called)

    def test_ssh_compute_remove_missing_key(self):
        self.setup_mocks_ssh_compute_remove(
            isfile=False,
            authorized_keys_lines=[UNIT2_PUBKEY_1])
        with patch_open() as (mock_open, mock_file):
            ssh_migrations.ssh_compute_remove(
                UNIT1_PUBKEY_1,
                'nova-compute-lxd')
            self.assertFalse(mock_file.write.called)

    @mock.patch.object(ssh_migrations, 'ssh_known_hosts_lines')
    @mock.patch.object(ssh_migrations, 'ssh_authorized_keys_lines')
    def test_get_ssh_settings(self, _ssh_authorized_keys_lines,
                              _ssh_known_hosts_lines):
        _ssh_authorized_keys_lines.return_value = PUB_KEYS
        _ssh_known_hosts_lines.return_value = HOST_KEYS
        expect = {
            'known_hosts_0': UNIT1_HOST_KEY_1,
            'known_hosts_1': UNIT1_HOST_KEY_2,
            'known_hosts_2': UNIT2_HOST_KEY_1,
            'known_hosts_3': UNIT2_HOST_KEY_2,
            'known_hosts_max_index': 4,
            'authorized_keys_0': UNIT1_PUBKEY_1,
            'authorized_keys_1': UNIT2_PUBKEY_1,
            'authorized_keys_max_index': 2,
        }
        self.assertEqual(
            ssh_migrations.get_ssh_settings('nova-compute-lxd'),
            expect)

    @mock.patch.object(ssh_migrations, 'ssh_known_hosts_lines')
    @mock.patch.object(ssh_migrations, 'ssh_authorized_keys_lines')
    def test_get_ssh_settings_user(self, _ssh_authorized_keys_lines,
                                   _ssh_known_hosts_lines):
        _ssh_authorized_keys_lines.return_value = PUB_KEYS
        _ssh_known_hosts_lines.return_value = HOST_KEYS
        expect = {
            'nova_known_hosts_0': UNIT1_HOST_KEY_1,
            'nova_known_hosts_1': UNIT1_HOST_KEY_2,
            'nova_known_hosts_2': UNIT2_HOST_KEY_1,
            'nova_known_hosts_3': UNIT2_HOST_KEY_2,
            'nova_known_hosts_max_index': 4,
            'nova_authorized_keys_0': UNIT1_PUBKEY_1,
            'nova_authorized_keys_1': UNIT2_PUBKEY_1,
            'nova_authorized_keys_max_index': 2,
        }
        self.assertEqual(
            ssh_migrations.get_ssh_settings('nova-compute-lxd', user='nova'),
            expect)

    @mock.patch.object(ssh_migrations, 'ssh_known_hosts_lines')
    @mock.patch.object(ssh_migrations, 'ssh_authorized_keys_lines')
    def test_get_ssh_settings_empty(self, _ssh_authorized_keys_lines,
                                    _ssh_known_hosts_lines):
        _ssh_authorized_keys_lines.return_value = []
        _ssh_known_hosts_lines.return_value = []
        self.assertEqual(
            ssh_migrations.get_ssh_settings('nova-compute-lxd'),
            {})

    @mock.patch.object(ssh_migrations, 'get_ssh_settings')
    def test_get_all_user_ssh_settings(self, _get_ssh_settings):
        def ssh_setiings(application_name, user=None):
            base_settings = {
                'known_hosts_0': UNIT1_HOST_KEY_1,
                'known_hosts_max_index': 1,
                'authorized_keys_0': UNIT1_PUBKEY_1,
                'authorized_keys_max_index': 1}
            user_settings = {
                'nova_known_hosts_0': UNIT1_HOST_KEY_1,
                'nova_known_hosts_max_index': 1,
                'nova_authorized_keys_0': UNIT1_PUBKEY_1,
                'nova_authorized_keys_max_index': 1}
            if user:
                return user_settings
            else:
                return base_settings
        _get_ssh_settings.side_effect = ssh_setiings
        expect = {
            'known_hosts_0': UNIT1_HOST_KEY_1,
            'known_hosts_max_index': 1,
            'authorized_keys_0': UNIT1_PUBKEY_1,
            'authorized_keys_max_index': 1,
            'nova_known_hosts_0': UNIT1_HOST_KEY_1,
            'nova_known_hosts_max_index': 1,
            'nova_authorized_keys_0': UNIT1_PUBKEY_1,
            'nova_authorized_keys_max_index': 1}
        self.assertEqual(
            ssh_migrations.get_all_user_ssh_settings('nova-compute-lxd'),
            expect)
