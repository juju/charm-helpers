import os
import mock
import json
import unittest
import sys
import tempfile

sys.modules['MySQLdb'] = mock.Mock()
from charmhelpers.contrib.database import mysql  # noqa


class MysqlTests(unittest.TestCase):
    def setUp(self):
        super(MysqlTests, self).setUp()

    @mock.patch.object(mysql.MySQLHelper, 'normalize_address')
    @mock.patch.object(mysql.MySQLHelper, 'get_mysql_password')
    @mock.patch.object(mysql.MySQLHelper, 'grant_exists')
    @mock.patch.object(mysql, 'relation_get')
    @mock.patch.object(mysql, 'related_units')
    @mock.patch.object(mysql, 'log')
    def test_get_allowed_units(self, mock_log, mock_related_units,
                               mock_relation_get,
                               mock_grant_exists,
                               mock_get_password,
                               mock_normalize_address):

        # echo
        mock_normalize_address.side_effect = lambda addr: addr

        def mock_rel_get(unit, rid):
            if unit == 'unit/0':
                # Non-prefixed settings
                d = {'private-address': '10.0.0.1',
                     'hostname': 'hostA'}
            elif unit == 'unit/1':
                # Containing prefixed settings
                d = {'private-address': '10.0.0.2',
                     'dbA_hostname': json.dumps(['10.0.0.2', '2001:db8:1::2'])}
            elif unit == 'unit/2':
                # No hostname
                d = {'private-address': '10.0.0.3'}

            return d

        mock_relation_get.side_effect = mock_rel_get
        mock_related_units.return_value = ['unit/0', 'unit/1', 'unit/2']

        helper = mysql.MySQLHelper('foo', 'bar', host='hostA')
        units = helper.get_allowed_units('dbA', 'userA')

        calls = [mock.call('dbA', 'userA', 'hostA'),
                 mock.call().__nonzero__(),
                 mock.call('dbA', 'userA', '10.0.0.2'),
                 mock.call().__nonzero__(),
                 mock.call('dbA', 'userA', '2001:db8:1::2'),
                 mock.call().__nonzero__(),
                 mock.call('dbA', 'userA', '10.0.0.3'),
                 mock.call().__nonzero__()]

        helper.grant_exists.assert_has_calls(calls)
        self.assertEqual(units, set(['unit/0', 'unit/1', 'unit/2']))

    @mock.patch('charmhelpers.contrib.network.ip.socket')
    @mock.patch.object(mysql, 'unit_get')
    @mock.patch.object(mysql, 'config_get')
    @mock.patch.object(mysql, 'log')
    def test_normalize_address(self, mock_log, mock_config_get, mock_unit_get,
                               mock_socket):
        helper = mysql.MySQLHelper('foo', 'bar', host='hostA')
        # prefer-ipv6
        mock_config_get.return_value = False
        # echo
        mock_socket.gethostbyname.side_effect = lambda addr: addr

        mock_unit_get.return_value = '10.0.0.1'
        out = helper.normalize_address('10.0.0.1')
        self.assertEqual('127.0.0.1', out)
        mock_config_get.assert_called_with('prefer-ipv6')

        mock_unit_get.return_value = '10.0.0.1'
        out = helper.normalize_address('10.0.0.2')
        self.assertEqual('10.0.0.2', out)
        mock_config_get.assert_called_with('prefer-ipv6')

        out = helper.normalize_address('2001:db8:1::1')
        self.assertEqual('2001:db8:1::1', out)
        mock_config_get.assert_called_with('prefer-ipv6')

        mock_socket.gethostbyname.side_effect = Exception
        out = helper.normalize_address('unresolvable')
        self.assertEqual('unresolvable', out)
        mock_config_get.assert_called_with('prefer-ipv6')

        # prefer-ipv6
        mock_config_get.return_value = True
        mock_socket.gethostbyname.side_effect = 'other'
        out = helper.normalize_address('unresolvable')
        self.assertEqual('unresolvable', out)
        mock_config_get.assert_called_with('prefer-ipv6')

    def test_passwd_keys(self):
        helper = mysql.MySQLHelper('foo', 'bar', host='hostA')
        self.assertEqual(list(helper.passwd_keys(None)), ['mysql.passwd'])
        self.assertEqual(list(helper.passwd_keys('auser')),
                         ['mysql-auser.passwd', 'auser.passwd'])

    @mock.patch.object(mysql.MySQLHelper, 'migrate_passwords_to_peer_relation')
    @mock.patch.object(mysql.MySQLHelper, 'get_mysql_password_on_disk')
    @mock.patch.object(mysql, 'peer_retrieve')
    def test_get_mysql_password_no_peer_passwd(self, mock_peer_retrieve,
                                               mock_get_disk_pw,
                                               mock_migrate_pw):
        helper = mysql.MySQLHelper('foo', 'bar', host='hostA')
        store = {}
        mock_peer_retrieve.side_effect = lambda key: store.get(key)
        mock_get_disk_pw.return_value = "disk-passwd"
        self.assertEqual(helper.get_mysql_password(), "disk-passwd")
        self.assertTrue(mock_migrate_pw.called)

    @mock.patch.object(mysql.MySQLHelper, 'migrate_passwords_to_peer_relation')
    @mock.patch.object(mysql.MySQLHelper, 'get_mysql_password_on_disk')
    @mock.patch.object(mysql, 'peer_retrieve')
    def test_get_mysql_password_peer_passwd(self, mock_peer_retrieve,
                                            mock_get_disk_pw, mock_migrate_pw):
        helper = mysql.MySQLHelper('foo', 'bar', host='hostA')
        store = {'mysql-userA.passwd': 'passwdA'}
        mock_peer_retrieve.side_effect = lambda key: store.get(key)
        mock_get_disk_pw.return_value = "disk-passwd"
        self.assertEqual(helper.get_mysql_password(username='userA'),
                         "passwdA")
        self.assertTrue(mock_migrate_pw.called)

    @mock.patch.object(mysql.MySQLHelper, 'migrate_passwords_to_peer_relation')
    @mock.patch.object(mysql.MySQLHelper, 'get_mysql_password_on_disk')
    @mock.patch.object(mysql, 'peer_retrieve')
    def test_get_mysql_password_peer_passwd_legacy(self, mock_peer_retrieve,
                                                   mock_get_disk_pw,
                                                   mock_migrate_pw):
        helper = mysql.MySQLHelper('foo', 'bar', host='hostA')
        store = {'userA.passwd': 'passwdA'}
        mock_peer_retrieve.side_effect = lambda key: store.get(key)
        mock_get_disk_pw.return_value = "disk-passwd"
        self.assertEqual(helper.get_mysql_password(username='userA'),
                         "passwdA")
        self.assertTrue(mock_migrate_pw.called)

    @mock.patch.object(mysql.MySQLHelper, 'migrate_passwords_to_peer_relation')
    @mock.patch.object(mysql.MySQLHelper, 'get_mysql_password_on_disk')
    @mock.patch.object(mysql, 'peer_retrieve')
    def test_get_mysql_password_peer_passwd_all(self, mock_peer_retrieve,
                                                mock_get_disk_pw,
                                                mock_migrate_pw):
        helper = mysql.MySQLHelper('foo', 'bar', host='hostA')
        # Add * so we can identify that the new format key takes precedence
        # if found.
        store = {'mysql-userA.passwd': 'passwdA',
                 'userA.passwd': 'passwdA*'}
        mock_peer_retrieve.side_effect = lambda key: store.get(key)
        mock_get_disk_pw.return_value = "disk-passwd"
        self.assertEqual(helper.get_mysql_password(username='userA'),
                         "passwdA")
        self.assertTrue(mock_migrate_pw.called)

    @mock.patch.object(mysql, 'peer_store')
    def test_migrate_passwords_to_peer_relation(self, mock_peer_store):
        files = {'mysql.passwd': '1',
                 'userA.passwd': '2',
                 'mysql-userA.passwd': '3'}
        store = {}

        def _store(key, val):
            store[key] = val

        tmpdir = tempfile.mkdtemp('charm-helpers-unit-tests')
        try:
            root_tmplt = "%s/mysql.passwd" % (tmpdir)
            helper = mysql.MySQLHelper(root_tmplt, None, host='hostA')
            for f in files:
                with open(os.path.join(tmpdir, f), 'w') as fd:
                    fd.write(files[f])

            mock_peer_store.side_effect = _store
            helper.migrate_passwords_to_peer_relation()

            calls = [mock.call('mysql.passwd', '1'),
                     mock.call('userA.passwd', '2'),
                     mock.call('mysql-userA.passwd', '3')]

            mock_peer_store.assert_has_calls(calls)
        finally:
            os.rmdir(tmpdir)

        # Note that legacy key/val is NOT overwritten
        self.assertEqual(store, {'mysql.passwd': '1',
                                 'userA.passwd': '2',
                                 'mysql-userA.passwd': '3'})


class PerconaTests(unittest.TestCase):

    def setUp(self):
        super(PerconaTests, self).setUp()

    @mock.patch.object(mysql.PerconaClusterHelper, 'get_mem_total')
    @mock.patch.object(mysql, 'config_get')
    @mock.patch.object(mysql, 'log')
    def test_parse_config_innodb_pool_fixed(self, log, config, mem):
        mem.return_value = "100G"
        config.return_value = {
            'innodb-buffer-pool-size': "50%",
        }

        helper = mysql.PerconaClusterHelper()
        mysql_config = helper.parse_config()

        self.assertEqual(mysql_config.get('innodb_buffer_pool_size'),
                         helper.human_to_bytes("50G"))

    @mock.patch.object(mysql.PerconaClusterHelper, 'get_mem_total')
    @mock.patch.object(mysql, 'config_get')
    @mock.patch.object(mysql, 'log')
    def test_parse_config_innodb_pool_not_set(self, mog, config, mem):
        mem.return_value = "100G"
        config.return_value = {
            'innodb-buffer-pool-size': '',
        }

        helper = mysql.PerconaClusterHelper()
        mysql_config = helper.parse_config()

        self.assertEqual(
            mysql_config.get('innodb_buffer_pool_size'),
            int(helper.human_to_bytes(mem.return_value) *
                helper.DEFAULT_INNODB_BUFFER_FACTOR))

    @mock.patch.object(mysql.PerconaClusterHelper, 'get_mem_total')
    @mock.patch.object(mysql, 'config_get')
    @mock.patch.object(mysql, 'log')
    def test_parse_config_innodb_buffer_unset(self, mog, config, mem):
        mem.return_value = "100G"
        config.return_value = {
            'innodb-buffer-pool-size': None,
            'dataset-size': None,
        }

        helper = mysql.PerconaClusterHelper()
        mysql_config = helper.parse_config()

        self.assertEqual(
            mysql_config.get('innodb-buffer-pool-size'),
            int(helper.human_to_bytes(mem.return_value) *
                helper.DEFAULT_INNODB_BUFFER_FACTOR))

    @mock.patch.object(mysql.PerconaClusterHelper, 'get_mem_total')
    @mock.patch.object(mysql, 'config_get')
    @mock.patch.object(mysql, 'log')
    def test_parse_config_innodb_dataset_size(self, mog, config, mem):
        mem.return_value = "100G"
        config.return_value = {
            'dataset-size': "10G",
        }

        helper = mysql.PerconaClusterHelper()
        mysql_config = helper.parse_config()

        self.assertEqual(
            mysql_config.get('innodb-buffer-pool-size'),
            int(helper.human_to_bytes("10G")))

    @mock.patch.object(mysql.PerconaClusterHelper, 'get_mem_total')
    @mock.patch.object(mysql, 'config_get')
    @mock.patch.object(mysql, 'log')
    def test_parse_config_wait_timeout(self, mog, config, mem):
        mem.return_value = "100G"

        timeout = 314
        config.return_value = {
            'wait-timeout': timeout,
        }

        helper = mysql.PerconaClusterHelper()
        mysql_config = helper.parse_config()

        self.assertEqual(
            mysql_config.get('wait_timeout'),
            timeout)
