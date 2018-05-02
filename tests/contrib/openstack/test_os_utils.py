import collections
import json
import mock
import six
import unittest

from charmhelpers.contrib.openstack import utils

if not six.PY3:
    builtin_open = '__builtin__.open'
else:
    builtin_open = 'builtins.open'


class UtilsTests(unittest.TestCase):
    def setUp(self):
        super(UtilsTests, self).setUp()

    def test_compare_openstack_comparator(self):
        self.assertTrue(utils.CompareOpenStackReleases('mitaka') < 'newton')
        self.assertTrue(utils.CompareOpenStackReleases('pike') > 'essex')

    @mock.patch.object(utils, 'config')
    @mock.patch('charmhelpers.contrib.openstack.utils.relation_set')
    @mock.patch('charmhelpers.contrib.openstack.utils.relation_ids')
    @mock.patch('charmhelpers.contrib.openstack.utils.get_ipv6_addr')
    def test_sync_db_with_multi_ipv6_addresses(self, mock_get_ipv6_addr,
                                               mock_relation_ids,
                                               mock_relation_set,
                                               mock_config):
        mock_config.return_value = None
        addr1 = '2001:db8:1:0:f816:3eff:fe45:7c/64'
        addr2 = '2001:db8:1:0:d0cf:528c:23eb:5000/64'
        mock_get_ipv6_addr.return_value = [addr1, addr2]
        mock_relation_ids.return_value = ['shared-db']

        utils.sync_db_with_multi_ipv6_addresses('testdb', 'testdbuser')
        hosts = json.dumps([addr1, addr2])
        mock_relation_set.assert_called_with(relation_id='shared-db',
                                             database='testdb',
                                             username='testdbuser',
                                             hostname=hosts)

    @mock.patch.object(utils, 'config')
    @mock.patch('charmhelpers.contrib.openstack.utils.relation_set')
    @mock.patch('charmhelpers.contrib.openstack.utils.relation_ids')
    @mock.patch('charmhelpers.contrib.openstack.utils.get_ipv6_addr')
    def test_sync_db_with_multi_ipv6_addresses_single(self, mock_get_ipv6_addr,
                                                      mock_relation_ids,
                                                      mock_relation_set,
                                                      mock_config):
        mock_config.return_value = None
        addr1 = '2001:db8:1:0:f816:3eff:fe45:7c/64'
        mock_get_ipv6_addr.return_value = [addr1]
        mock_relation_ids.return_value = ['shared-db']

        utils.sync_db_with_multi_ipv6_addresses('testdb', 'testdbuser')
        hosts = json.dumps([addr1])
        mock_relation_set.assert_called_with(relation_id='shared-db',
                                             database='testdb',
                                             username='testdbuser',
                                             hostname=hosts)

    @mock.patch.object(utils, 'config')
    @mock.patch('charmhelpers.contrib.openstack.utils.relation_set')
    @mock.patch('charmhelpers.contrib.openstack.utils.relation_ids')
    @mock.patch('charmhelpers.contrib.openstack.utils.get_ipv6_addr')
    def test_sync_db_with_multi_ipv6_addresses_w_prefix(self,
                                                        mock_get_ipv6_addr,
                                                        mock_relation_ids,
                                                        mock_relation_set,
                                                        mock_config):
        mock_config.return_value = None
        addr1 = '2001:db8:1:0:f816:3eff:fe45:7c/64'
        mock_get_ipv6_addr.return_value = [addr1]
        mock_relation_ids.return_value = ['shared-db']

        utils.sync_db_with_multi_ipv6_addresses('testdb', 'testdbuser',
                                                relation_prefix='bungabunga')
        hosts = json.dumps([addr1])
        mock_relation_set.assert_called_with(relation_id='shared-db',
                                             bungabunga_database='testdb',
                                             bungabunga_username='testdbuser',
                                             bungabunga_hostname=hosts)

    @mock.patch.object(utils, 'config')
    @mock.patch('charmhelpers.contrib.openstack.utils.relation_set')
    @mock.patch('charmhelpers.contrib.openstack.utils.relation_ids')
    @mock.patch('charmhelpers.contrib.openstack.utils.get_ipv6_addr')
    def test_sync_db_with_multi_ipv6_addresses_vips(self, mock_get_ipv6_addr,
                                                    mock_relation_ids,
                                                    mock_relation_set,
                                                    mock_config):
        addr1 = '2001:db8:1:0:f816:3eff:fe45:7c/64'
        addr2 = '2001:db8:1:0:d0cf:528c:23eb:5000/64'
        vip1 = '2001:db8:1:0:f816:3eff:32b3:7c'
        vip2 = '2001:db8:1:0:f816:3eff:32b3:7d'
        mock_config.return_value = '%s 10.0.0.1 %s' % (vip1, vip2)

        mock_get_ipv6_addr.return_value = [addr1, addr2]
        mock_relation_ids.return_value = ['shared-db']

        utils.sync_db_with_multi_ipv6_addresses('testdb', 'testdbuser')
        hosts = json.dumps([addr1, addr2, vip1, vip2])
        mock_relation_set.assert_called_with(relation_id='shared-db',
                                             database='testdb',
                                             username='testdbuser',
                                             hostname=hosts)

    @mock.patch('uuid.uuid4')
    @mock.patch('charmhelpers.contrib.openstack.utils.related_units')
    @mock.patch('charmhelpers.contrib.openstack.utils.relation_set')
    @mock.patch('charmhelpers.contrib.openstack.utils.relation_ids')
    def test_remote_restart(self, mock_relation_ids, mock_relation_set,
                            mock_related_units, mock_uuid4):
        mock_relation_ids.return_value = ['neutron-plugin-api-subordinate:8']
        mock_related_units.return_value = ['neutron-api/0']
        mock_uuid4.return_value = 'uuid4'
        utils.remote_restart('neutron-plugin-api-subordinate')
        mock_relation_set.assert_called_with(
            relation_id='neutron-plugin-api-subordinate:8',
            relation_settings={'restart-trigger': 'uuid4'}
        )

    @mock.patch.object(utils, 'config')
    @mock.patch('charmhelpers.contrib.openstack.utils.get_os_codename_package')
    @mock.patch('charmhelpers.contrib.openstack.utils.'
                'get_os_codename_install_source')
    def test_os_release(self, mock_get_os_codename_install_source,
                        mock_get_os_codename_package,
                        mock_config):
        # Wipe the modules cached os_rel
        utils._os_rel = None
        mock_get_os_codename_install_source.return_value = None
        mock_get_os_codename_package.return_value = None
        mock_config.return_value = 'cloud-pocket'
        self.assertEqual(utils.os_release('my-pkg'), 'essex')
        mock_get_os_codename_install_source.assert_called_once_with(
            'cloud-pocket')
        mock_get_os_codename_package.assert_called_once_with(
            'my-pkg', fatal=False)
        # Next call to os_release should pickup cached version
        mock_get_os_codename_install_source.reset_mock()
        mock_get_os_codename_package.reset_mock()
        self.assertEqual(utils.os_release('my-pkg'), 'essex')
        self.assertFalse(mock_get_os_codename_install_source.called)
        self.assertFalse(mock_get_os_codename_package.called)
        # Call os_release and bypass cache
        mock_get_os_codename_install_source.reset_mock()
        mock_get_os_codename_package.reset_mock()
        self.assertEqual(utils.os_release('my-pkg', reset_cache=True),
                         'essex')
        mock_get_os_codename_install_source.assert_called_once_with(
            'cloud-pocket')
        mock_get_os_codename_package.assert_called_once_with(
            'my-pkg', fatal=False)

    @mock.patch.object(utils, 'os_release')
    @mock.patch.object(utils, 'get_os_codename_install_source')
    def test_enable_memcache(self, _get_os_codename_install_source,
                             _os_release):
        # Check call with 'release'
        self.assertFalse(utils.enable_memcache(release='icehouse'))
        self.assertTrue(utils.enable_memcache(release='ocata'))
        # Check call with 'source'
        _os_release.return_value = None
        _get_os_codename_install_source.return_value = 'icehouse'
        self.assertFalse(utils.enable_memcache(source='distro'))
        _os_release.return_value = None
        _get_os_codename_install_source.return_value = 'ocata'
        self.assertTrue(utils.enable_memcache(source='distro'))
        # Check call with 'package'
        _os_release.return_value = 'icehouse'
        _get_os_codename_install_source.return_value = None
        self.assertFalse(utils.enable_memcache(package='pkg1'))
        _os_release.return_value = 'ocata'
        _get_os_codename_install_source.return_value = None
        self.assertTrue(utils.enable_memcache(package='pkg1'))

    @mock.patch.object(utils, 'enable_memcache')
    def test_enable_token_cache_pkgs(self, _enable_memcache):
        _enable_memcache.return_value = False
        self.assertEqual(utils.token_cache_pkgs(source='distro'), [])
        _enable_memcache.return_value = True
        self.assertEqual(utils.token_cache_pkgs(source='distro'),
                         ['memcached', 'python-memcache'])

    def test_update_json_file(self):
        TEST_POLICY = """{
        "delete_image_location": "",
        "get_image_location": "",
        "set_image_location": "",
        "extra_property": "False"
        }"""

        TEST_POLICY_FILE = "/etc/glance/policy.json"

        items_to_update = {
            "get_image_location": "role:admin",
            "extra_policy": "extra",
        }

        mock_open = mock.mock_open(read_data=TEST_POLICY)
        with mock.patch(builtin_open, mock_open) as mock_file:
            utils.update_json_file(TEST_POLICY_FILE, {})
            self.assertFalse(mock_file.called)

            utils.update_json_file(TEST_POLICY_FILE, items_to_update)
            mock_file.assert_has_calls([
                mock.call(TEST_POLICY_FILE),
                mock.call(TEST_POLICY_FILE, 'w'),
            ], any_order=True)

        modified_policy = json.loads(TEST_POLICY)
        modified_policy.update(items_to_update)
        mock_open().write.assert_called_with(
            json.dumps(modified_policy, indent=4, sort_keys=True))

        tmp = json.loads(TEST_POLICY)
        tmp.update(items_to_update)
        TEST_POLICY = json.dumps(tmp)
        mock_open = mock.mock_open(read_data=TEST_POLICY)
        with mock.patch(builtin_open, mock_open) as mock_file:
            utils.update_json_file(TEST_POLICY_FILE, items_to_update)
            mock_file.assert_has_calls([
                mock.call(TEST_POLICY_FILE),
            ], any_order=True)

    def test_ordered(self):
        data = {'one': 1, 'two': 2, 'three': 3}
        expected = [('one', 1), ('three', 3), ('two', 2)]
        self.assertSequenceEqual(expected,
                                 [x for x in utils.ordered(data).items()])

        data = {
            'one': 1,
            'two': 2,
            'three': {
                'uno': 1,
                'dos': 2,
                'tres': 3
            }
        }
        expected = collections.OrderedDict()
        expected['one'] = 1
        nested = collections.OrderedDict()
        nested['dos'] = 2
        nested['tres'] = 3
        nested['uno'] = 1
        expected['three'] = nested
        expected['two'] = 2
        self.assertEqual(expected, utils.ordered(data))

        self.assertRaises(ValueError, utils.ordered, "foo")
