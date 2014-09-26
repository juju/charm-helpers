import json
import mock
import unittest

from charmhelpers.contrib.openstack import utils


class UtilsTests(unittest.TestCase):
    def setUp(self):
        super(UtilsTests, self).setUp()

    @mock.patch('charmhelpers.contrib.openstack.utils.relation_set')
    @mock.patch('charmhelpers.contrib.openstack.utils.config')
    @mock.patch('charmhelpers.contrib.openstack.utils.relation_ids')
    @mock.patch('charmhelpers.contrib.openstack.utils.get_ipv6_addr')
    def test_sync_db_with_multi_ipv6_addresses(self, mock_get_ipv6_addr,
                                               mock_relation_ids, mock_config,
                                               mock_relation_set):
        addr1 = '2001:db8:1:0:f816:3eff:fe45:7c/64'
        addr2 = '2001:db8:1:0:d0cf:528c:23eb:5000/64'
        mock_get_ipv6_addr.return_value = [addr1, addr2]
        mock_relation_ids.return_value = ['shared-db']

        config = {'database': 'big', 'database-user': 'wind'}

        class cls_mock_config(object):

            def __call__(self, key):
                return config[key]

        mock_config.side_effect = cls_mock_config()
        utils.sync_db_with_multi_ipv6_addresses()
        hosts = json.dumps([addr1, addr2])
        mock_relation_set.assert_called_with(relation_id='shared-db',
                                             database='big',
                                             username='wind',
                                             hostname=hosts)

    @mock.patch('charmhelpers.contrib.openstack.utils.relation_set')
    @mock.patch('charmhelpers.contrib.openstack.utils.config')
    @mock.patch('charmhelpers.contrib.openstack.utils.relation_ids')
    @mock.patch('charmhelpers.contrib.openstack.utils.get_ipv6_addr')
    def test_sync_db_with_multi_ipv6_addresses_single(self, mock_get_ipv6_addr,
                                                      mock_relation_ids,
                                                      mock_config,
                                                      mock_relation_set):
        addr1 = '2001:db8:1:0:f816:3eff:fe45:7c/64'
        mock_get_ipv6_addr.return_value = [addr1]
        mock_relation_ids.return_value = ['shared-db']

        config = {'database': 'big', 'database-user': 'wind'}

        class cls_mock_config(object):

            def __call__(self, key):
                return config[key]

        mock_config.side_effect = cls_mock_config()
        utils.sync_db_with_multi_ipv6_addresses()
        hosts = json.dumps([addr1])
        mock_relation_set.assert_called_with(relation_id='shared-db',
                                             database='big',
                                             username='wind',
                                             hostname=hosts)
