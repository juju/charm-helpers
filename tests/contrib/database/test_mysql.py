import mock
import json
import unittest
import sys

sys.modules['MySQLdb'] = mock.Mock()
from charmhelpers.contrib.database import mysql  # noqa


class MysqlTests(unittest.TestCase):
    def setUp(self):
        super(MysqlTests, self).setUp()

    @mock.patch.object(mysql.MySQLHelper, 'get_mysql_password')
    @mock.patch.object(mysql.MySQLHelper, 'grant_exists')
    @mock.patch.object(mysql, 'relation_get')
    @mock.patch.object(mysql, 'related_units')
    @mock.patch.object(mysql, 'log')
    def test_get_allowed_units(self, mock_log, mock_related_units,
                               mock_relation_get,
                               mock_grant_exists,
                               mock_get_password):

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


class PerconaTests(unittest.TestCase):

    def setUp(self):
        super(PerconaTests, self).setUp()

    @mock.patch.object(mysql.PerconaClusterHelper, 'get_mem_total')
    @mock.patch.object(mysql, 'config_get')
    def test_parse_config_innodb_pool_fixed(self, config, mem):
        """Checks that a fixed buffer pool size uses the indicated amount of
        dataset-size"""
        mem.return_value = "100G"
        config.return_value = {
            'dataset-size': "100%",
            'innodb-buffer-pool-size': "50%",
        }

        helper = mysql.PerconaClusterHelper()
        mysql_config = helper.parse_config()

        self.assertEqual(mysql_config.get('dataset_bytes'),
                         helper.human_to_bytes(mem.return_value))

        self.assertEqual(mysql_config.get('innodb_buffer_pool_size'),
                         helper.human_to_bytes("50G"))

    @mock.patch.object(mysql.PerconaClusterHelper, 'get_mem_total')
    @mock.patch.object(mysql, 'config_get')
    def test_parse_config_innodb_pool_not_set(self, config, mem):
        mem.return_value = "100G"
        config.return_value = {
            'dataset-size': "32G",
        }

        helper = mysql.PerconaClusterHelper()
        mysql_config = helper.parse_config()

        self.assertEqual(mysql_config.get('dataset_bytes'),
                         helper.human_to_bytes(
                             config.return_value.get('dataset-size')))

        dataset_bytes = helper.human_to_bytes(config.return_value.get(
            'dataset-size'))

        # Check if innodb_buffer_pool_size is set to dataset-size + 10%
        self.assertEqual(
            mysql_config.get('innodb_buffer_pool_size'),
            int(dataset_bytes + (
                dataset_bytes * helper.DEFAULT_INNODB_POOL_FACTOR))
        )

    @mock.patch.object(mysql.PerconaClusterHelper, 'get_mem_total')
    @mock.patch.object(mysql, 'config_get')
    @mock.patch.object(mysql, 'log')
    def test_parse_config_warn_dataset(self, log, config, mem):
        mem.return_value = "100G"
        config.return_value = {
            'dataset-size': "200G",
        }

        helper = mysql.PerconaClusterHelper()

        helper.parse_config()
        log.assert_has_calls(
            mock.call("Dataset size: 214748364800 is greater than current system's available RAM: 107374182400",
                      level='WARN')
        )
