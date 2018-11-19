import os
import mock
import json
import unittest
import sys
import shutil
import tempfile


sys.modules['MySQLdb'] = mock.Mock()
from charmhelpers.contrib.database import mysql  # noqa


class MysqlTests(unittest.TestCase):
    def setUp(self):
        super(MysqlTests, self).setUp()

    def test_connect_host_defined(self):
        helper = mysql.MySQLHelper('foo', 'bar', host='hostA')
        with mock.patch.object(mysql, 'log'):
            helper.connect(user='user', password='password', host='1.1.1.1')
        mysql.MySQLdb.connect.assert_called_with(
            passwd='password', host='1.1.1.1', user='user')

    def test_connect_host_not_defined(self):
        helper = mysql.MySQLHelper('foo', 'bar')
        with mock.patch.object(mysql, 'log'):
            helper.connect(user='user', password='password')
        mysql.MySQLdb.connect.assert_called_with(
            passwd='password', host='localhost', user='user')

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
                 mock.call('dbA', 'userA', '10.0.0.2'),
                 mock.call('dbA', 'userA', '2001:db8:1::2'),
                 mock.call('dbA', 'userA', '10.0.0.3')]

        helper.grant_exists.assert_has_calls(calls, any_order=True)
        self.assertEqual(units, set(['unit/0', 'unit/1', 'unit/2']))

    @mock.patch('charmhelpers.contrib.network.ip.log',
                lambda *args, **kwargs: None)
    @mock.patch('charmhelpers.contrib.network.ip.ns_query')
    @mock.patch('charmhelpers.contrib.network.ip.socket')
    @mock.patch.object(mysql, 'unit_get')
    @mock.patch.object(mysql, 'config_get')
    @mock.patch.object(mysql, 'log')
    def test_normalize_address(self, mock_log, mock_config_get, mock_unit_get,
                               mock_socket, mock_ns_query):
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
        mock_ns_query.return_value = None
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

    @mock.patch.object(mysql.MySQLHelper, 'migrate_passwords_to_leader_storage')
    @mock.patch.object(mysql.MySQLHelper, 'get_mysql_password_on_disk')
    @mock.patch.object(mysql, 'leader_get')
    def test_get_mysql_password_no_peer_passwd(self, mock_leader_get,
                                               mock_get_disk_pw,
                                               mock_migrate_pw):
        helper = mysql.MySQLHelper('foo', 'bar', host='hostA')
        store = {}
        mock_leader_get.side_effect = lambda key: store.get(key)
        mock_get_disk_pw.return_value = "disk-passwd"
        self.assertEqual(helper.get_mysql_password(), "disk-passwd")
        self.assertTrue(mock_migrate_pw.called)

    @mock.patch.object(mysql.MySQLHelper, 'migrate_passwords_to_leader_storage')
    @mock.patch.object(mysql.MySQLHelper, 'get_mysql_password_on_disk')
    @mock.patch.object(mysql, 'leader_get')
    def test_get_mysql_password_peer_passwd(self, mock_leader_get,
                                            mock_get_disk_pw, mock_migrate_pw):
        helper = mysql.MySQLHelper('foo', 'bar', host='hostA')
        store = {'mysql-userA.passwd': 'passwdA'}
        mock_leader_get.side_effect = lambda key: store.get(key)
        mock_get_disk_pw.return_value = "disk-passwd"
        self.assertEqual(helper.get_mysql_password(username='userA'),
                         "passwdA")
        self.assertTrue(mock_migrate_pw.called)

    @mock.patch.object(mysql.MySQLHelper, 'migrate_passwords_to_leader_storage')
    @mock.patch.object(mysql.MySQLHelper, 'get_mysql_password_on_disk')
    @mock.patch.object(mysql, 'leader_get')
    def test_get_mysql_password_peer_passwd_legacy(self, mock_leader_get,
                                                   mock_get_disk_pw,
                                                   mock_migrate_pw):
        helper = mysql.MySQLHelper('foo', 'bar', host='hostA')
        store = {'userA.passwd': 'passwdA'}
        mock_leader_get.side_effect = lambda key: store.get(key)
        mock_get_disk_pw.return_value = "disk-passwd"
        self.assertEqual(helper.get_mysql_password(username='userA'),
                         "passwdA")
        self.assertTrue(mock_migrate_pw.called)

    @mock.patch.object(mysql.MySQLHelper, 'migrate_passwords_to_leader_storage')
    @mock.patch.object(mysql.MySQLHelper, 'get_mysql_password_on_disk')
    @mock.patch.object(mysql, 'leader_get')
    def test_get_mysql_password_peer_passwd_all(self, mock_leader_get,
                                                mock_get_disk_pw,
                                                mock_migrate_pw):
        helper = mysql.MySQLHelper('foo', 'bar', host='hostA')
        # Add * so we can identify that the new format key takes precedence
        # if found.
        store = {'mysql-userA.passwd': 'passwdA',
                 'userA.passwd': 'passwdA*'}
        mock_leader_get.side_effect = lambda key: store.get(key)
        mock_get_disk_pw.return_value = "disk-passwd"
        self.assertEqual(helper.get_mysql_password(username='userA'),
                         "passwdA")
        self.assertTrue(mock_migrate_pw.called)

    @mock.patch.object(mysql.MySQLHelper, 'set_mysql_password')
    def test_set_mysql_root_password(self, mock_set_passwd):
        helper = mysql.MySQLHelper('foo', 'bar', host='hostA')
        helper.set_mysql_root_password(password='1234')
        mock_set_passwd.assert_called_with('root', '1234')

    @mock.patch.object(mysql, 'log', lambda *args, **kwargs: None)
    @mock.patch.object(mysql, 'is_leader')
    @mock.patch.object(mysql, 'leader_get')
    @mock.patch.object(mysql, 'leader_set')
    @mock.patch.object(mysql, 'CompareHostReleases')
    @mock.patch.object(mysql.MySQLHelper, 'get_mysql_password')
    @mock.patch.object(mysql.MySQLHelper, 'connect')
    def test_set_mysql_password(self, mock_connect, mock_get_passwd,
                                mock_compare_releases, mock_leader_set,
                                mock_leader_get, mock_is_leader):
        mock_connection = mock.MagicMock()
        mock_cursor = mock.MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_get_passwd.return_value = 'asdf'
        mock_is_leader.return_value = True
        mock_leader_get.return_value = '1234'
        mock_compare_releases.return_value = 'artful'

        helper = mysql.MySQLHelper('foo', 'bar', host='hostA')
        helper.connection = mock_connection

        helper.set_mysql_password(username='root', password='1234')

        mock_connect.assert_has_calls(
            [mock.call(user='root', password='asdf'),  # original password
             mock.call(user='root', password='1234')])  # new password
        mock_leader_get.assert_has_calls([mock.call('mysql.passwd')])
        mock_leader_set.assert_has_calls(
            [mock.call(settings={'mysql.passwd': '1234'})]
        )
        SQL_UPDATE_PASSWD = ("UPDATE mysql.user SET password = "
                             "PASSWORD( %s ) WHERE user = %s;")
        mock_cursor.assert_has_calls(
            [mock.call.execute(SQL_UPDATE_PASSWD, ('1234', 'root')),
             mock.call.execute('FLUSH PRIVILEGES;'),
             mock.call.close(),
             mock.call.execute('select 1;'),
             mock.call.close()]
        )

        # make sure for the non-leader leader-set is not called
        mock_is_leader.return_value = False
        mock_leader_set.reset_mock()
        helper.set_mysql_password(username='root', password='1234')
        mock_leader_set.assert_not_called()

        mock_compare_releases.return_value = 'bionic'
        helper.set_mysql_password(username='root', password='1234')
        SQL_UPDATE_PASSWD = ("UPDATE mysql.user SET "
                             "authentication_string = "
                             "PASSWORD( %s ) WHERE user = %s;")
        mock_cursor.assert_has_calls(
            [mock.call.execute(SQL_UPDATE_PASSWD, ('1234', 'root')),
             mock.call.execute('FLUSH PRIVILEGES;'),
             mock.call.close(),
             mock.call.execute('select 1;'),
             mock.call.close()]
        )

    @mock.patch.object(mysql, 'leader_get')
    @mock.patch.object(mysql, 'leader_set')
    @mock.patch.object(mysql.MySQLHelper, 'get_mysql_password')
    @mock.patch.object(mysql.MySQLHelper, 'connect')
    def test_set_mysql_password_fail_to_connect(self, mock_connect,
                                                mock_get_passwd,
                                                mock_leader_set,
                                                mock_leader_get):

        class FakeOperationalError(Exception):
            pass

        def fake_connect(*args, **kwargs):
            raise FakeOperationalError('foobar')

        mysql.MySQLdb.OperationalError = FakeOperationalError
        helper = mysql.MySQLHelper('foo', 'bar', host='hostA')
        mock_connect.side_effect = fake_connect
        self.assertRaises(mysql.MySQLSetPasswordError,
                          helper.set_mysql_password,
                          username='root', password='1234')

    @mock.patch.object(mysql, 'leader_get')
    @mock.patch.object(mysql, 'leader_set')
    @mock.patch.object(mysql.MySQLHelper, 'get_mysql_password')
    @mock.patch.object(mysql.MySQLHelper, 'connect')
    def test_set_mysql_password_fail_to_connect2(self, mock_connect,
                                                 mock_get_passwd,
                                                 mock_leader_set,
                                                 mock_leader_get):

        class FakeOperationalError(Exception):
            def __str__(self):
                return 'some-error'

        operational_error = FakeOperationalError('foobar')

        def fake_connect(user, password):
            # fail for the new password
            if user == 'root' and password == '1234':
                raise operational_error
            else:
                return mock.MagicMock()

        mysql.MySQLdb.OperationalError = FakeOperationalError
        helper = mysql.MySQLHelper('foo', 'bar', host='hostA')
        helper.connection = mock.MagicMock()
        mock_connect.side_effect = fake_connect
        with self.assertRaises(mysql.MySQLSetPasswordError) as cm:
            helper.set_mysql_password(username='root', password='1234')

        ex = cm.exception
        self.assertEqual(ex.args[0], 'Cannot connect using new password: some-error')
        self.assertEqual(ex.args[1], operational_error)

    @mock.patch.object(mysql, 'is_leader')
    @mock.patch.object(mysql, 'leader_set')
    def test_migrate_passwords_to_leader_storage(self, mock_leader_set,
                                                 mock_is_leader):
        files = {'mysql.passwd': '1',
                 'userA.passwd': '2',
                 'mysql-userA.passwd': '3'}
        store = {}

        def _store(settings):
            store.update(settings)

        mock_is_leader.return_value = True

        tmpdir = tempfile.mkdtemp('charm-helpers-unit-tests')
        try:
            root_tmplt = "%s/mysql.passwd" % (tmpdir)
            helper = mysql.MySQLHelper(root_tmplt, None, host='hostA')
            for f in files:
                with open(os.path.join(tmpdir, f), 'w') as fd:
                    fd.write(files[f])

            mock_leader_set.side_effect = _store
            helper.migrate_passwords_to_leader_storage()

            calls = [mock.call(settings={'mysql.passwd': '1'}),
                     mock.call(settings={'userA.passwd': '2'}),
                     mock.call(settings={'mysql-userA.passwd': '3'})]

            mock_leader_set.assert_has_calls(calls,
                                             any_order=True)
        finally:
            shutil.rmtree(tmpdir)

        # Note that legacy key/val is NOT overwritten
        self.assertEqual(store, {'mysql.passwd': '1',
                                 'userA.passwd': '2',
                                 'mysql-userA.passwd': '3'})

    @mock.patch.object(mysql, 'log', lambda *args, **kwargs: None)
    @mock.patch.object(mysql, 'is_leader')
    @mock.patch.object(mysql, 'leader_set')
    def test_migrate_passwords_to_leader_storage_not_leader(self, mock_leader_set,
                                                            mock_is_leader):
        mock_is_leader.return_value = False
        tmpdir = tempfile.mkdtemp('charm-helpers-unit-tests')
        try:
            root_tmplt = "%s/mysql.passwd" % (tmpdir)
            helper = mysql.MySQLHelper(root_tmplt, None, host='hostA')
            helper.migrate_passwords_to_leader_storage()
        finally:
            shutil.rmtree(tmpdir)
        mock_leader_set.assert_not_called()


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
            helper.DEFAULT_INNODB_BUFFER_SIZE_MAX)

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
            mysql_config.get('innodb_buffer_pool_size'),
            helper.DEFAULT_INNODB_BUFFER_SIZE_MAX)

    @mock.patch.object(mysql.PerconaClusterHelper, 'get_mem_total')
    @mock.patch.object(mysql, 'config_get')
    @mock.patch.object(mysql, 'log')
    def test_parse_config_innodb_buffer_unset_small(self, mog,
                                                    config, mem):
        mem.return_value = "512M"
        config.return_value = {
            'innodb-buffer-pool-size': None,
            'dataset-size': None,
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
    def test_parse_config_innodb_dataset_size(self, mog, config, mem):
        mem.return_value = "100G"
        config.return_value = {
            'dataset-size': "10G",
        }

        helper = mysql.PerconaClusterHelper()
        mysql_config = helper.parse_config()

        self.assertEqual(
            mysql_config.get('innodb_buffer_pool_size'),
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

    @mock.patch.object(mysql.PerconaClusterHelper, 'get_mem_total')
    @mock.patch.object(mysql, 'config_get')
    @mock.patch.object(mysql, 'log')
    def test_parse_config_tuning_level(self, mog,
                                       config, mem):
        mem.return_value = "512M"
        config.return_value = {
            'tuning-level': 'safest',
        }

        helper = mysql.PerconaClusterHelper()
        mysql_config = helper.parse_config()

        self.assertEqual(
            mysql_config.get('innodb_flush_log_at_trx_commit'),
            1
        )

    @mock.patch.object(mysql.PerconaClusterHelper, 'get_mem_total')
    @mock.patch.object(mysql, 'config_get')
    @mock.patch.object(mysql, 'log')
    def test_parse_config_tuning_level_fast(self, mog,
                                            config, mem):
        mem.return_value = "512M"
        config.return_value = {
            'tuning-level': 'fast',
        }

        helper = mysql.PerconaClusterHelper()
        mysql_config = helper.parse_config()

        self.assertEqual(
            mysql_config.get('innodb_flush_log_at_trx_commit'),
            2
        )

    @mock.patch.object(mysql.PerconaClusterHelper, 'get_mem_total')
    @mock.patch.object(mysql, 'config_get')
    @mock.patch.object(mysql, 'log')
    def test_parse_config_tuning_level_unsafe(self, mog,
                                              config, mem):
        mem.return_value = "512M"
        config.return_value = {
            'tuning-level': 'unsafe',
        }

        helper = mysql.PerconaClusterHelper()
        mysql_config = helper.parse_config()

        self.assertEqual(
            mysql_config.get('innodb_flush_log_at_trx_commit'),
            0
        )

    @mock.patch.object(mysql.PerconaClusterHelper, 'get_mem_total')
    @mock.patch.object(mysql, 'config_get')
    @mock.patch.object(mysql, 'log')
    def test_parse_config_innodb_valid_values(self, mog,
                                              config, mem):
        mem.return_value = "512M"
        config.return_value = {
            'innodb-change-buffering': 'all',
            'innodb-io-capacity': 100,
        }

        helper = mysql.PerconaClusterHelper()
        mysql_config = helper.parse_config()

        self.assertEqual(
            mysql_config.get('innodb_change_buffering'),
            'all'
        )

        self.assertEqual(
            mysql_config.get('innodb_io_capacity'),
            100
        )

    @mock.patch.object(mysql.PerconaClusterHelper, 'get_mem_total')
    @mock.patch.object(mysql, 'config_get')
    @mock.patch.object(mysql, 'log')
    def test_parse_config_innodb_invalid_values(self, mog,
                                                config, mem):
        mem.return_value = "512M"
        config.return_value = {
            'innodb-change-buffering': 'invalid',
        }

        helper = mysql.PerconaClusterHelper()
        mysql_config = helper.parse_config()

        self.assertTrue('innodb_change_buffering' not in mysql_config)
        self.assertTrue('innodb_io_capacity' not in mysql_config)
