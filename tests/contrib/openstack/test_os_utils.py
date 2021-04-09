import collections
import copy
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

    @mock.patch.object(utils, 'lsb_release')
    @mock.patch.object(utils, 'config')
    @mock.patch('charmhelpers.contrib.openstack.utils.get_os_codename_package')
    @mock.patch('charmhelpers.contrib.openstack.utils.'
                'get_os_codename_install_source')
    def test_os_release(self, mock_get_os_codename_install_source,
                        mock_get_os_codename_package,
                        mock_config, mock_lsb_release):
        # Wipe the modules cached os_rel
        utils._os_rel = None
        mock_lsb_release.return_value = {"DISTRIB_CODENAME": "trusty"}
        mock_get_os_codename_install_source.return_value = None
        mock_get_os_codename_package.return_value = None
        mock_config.return_value = 'cloud-pocket'
        self.assertEqual(utils.os_release('my-pkg'), 'icehouse')
        mock_get_os_codename_install_source.assert_called_once_with(
            'cloud-pocket')
        mock_get_os_codename_package.assert_called_once_with(
            'my-pkg', fatal=False)
        mock_config.assert_called_once_with('openstack-origin')
        # Next call to os_release should pickup cached version
        mock_get_os_codename_install_source.reset_mock()
        mock_get_os_codename_package.reset_mock()
        self.assertEqual(utils.os_release('my-pkg'), 'icehouse')
        self.assertFalse(mock_get_os_codename_install_source.called)
        self.assertFalse(mock_get_os_codename_package.called)
        # Call os_release and bypass cache
        mock_lsb_release.return_value = {"DISTRIB_CODENAME": "xenial"}
        mock_get_os_codename_install_source.reset_mock()
        mock_get_os_codename_package.reset_mock()
        self.assertEqual(utils.os_release('my-pkg', reset_cache=True),
                         'mitaka')
        mock_get_os_codename_install_source.assert_called_once_with(
            'cloud-pocket')
        mock_get_os_codename_package.assert_called_once_with(
            'my-pkg', fatal=False)
        # Override base
        mock_lsb_release.return_value = {"DISTRIB_CODENAME": "xenial"}
        mock_get_os_codename_install_source.reset_mock()
        mock_get_os_codename_package.reset_mock()
        self.assertEqual(utils.os_release('my-pkg', reset_cache=True, base="ocata"),
                         'ocata')
        mock_get_os_codename_install_source.assert_called_once_with(
            'cloud-pocket')
        mock_get_os_codename_package.assert_called_once_with(
            'my-pkg', fatal=False)
        # Override source key
        mock_config.reset_mock()
        mock_get_os_codename_install_source.reset_mock()
        mock_get_os_codename_package.reset_mock()
        mock_get_os_codename_package.return_value = None
        utils.os_release('my-pkg', reset_cache=True, source_key='source')
        mock_config.assert_called_once_with('source')
        mock_get_os_codename_install_source.assert_called_once_with(
            'cloud-pocket')

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

    def test_sequence_status_check_functions(self):
        # all messages are reported and the highest priority status "wins"
        f1 = mock.Mock(return_value=('blocked', 'status 1'))
        f2 = mock.Mock(return_value=('', 'status 2'))
        f3 = mock.Mock(return_value=('maintenance', 'status 3'))
        f = utils.sequence_status_check_functions(f1, f2, f3)
        expected = ('blocked', 'status 1, status 2, status 3')
        result = f(mock.Mock())
        self.assertEquals(result, expected)
        # empty status must be replaced by "unknown"
        f4 = mock.Mock(return_value=('', 'status 4'))
        f5 = mock.Mock(return_value=('', 'status 5'))
        f = utils.sequence_status_check_functions(f4, f5)
        expected = ('unknown', 'status 4, status 5')
        result = f(mock.Mock())
        self.assertEquals(result, expected)
        # sequencing 0 status checks must return state 'unknown', ''
        f = utils.sequence_status_check_functions()
        expected = ('unknown', '')
        result = f(mock.Mock())
        self.assertEquals(result, expected)

    @mock.patch.object(utils, 'relation_get')
    @mock.patch.object(utils, 'related_units')
    @mock.patch.object(utils, 'relation_ids')
    @mock.patch.object(utils, 'container_scoped_relations')
    def test_container_scoped_relation_get(
            self,
            mock_container_scoped_relations,
            mock_relation_ids,
            mock_related_units,
            mock_relation_get):
        mock_container_scoped_relations.return_value = [
            'relation1', 'relation2']
        mock_relation_ids.return_value = ['rid']
        mock_related_units.return_value = ['unit']

        for rdata in utils.container_scoped_relation_get():
            pass
        mock_relation_ids.assert_has_calls([
            mock.call('relation1'),
            mock.call('relation2')])
        mock_relation_get.assert_has_calls([
            mock.call(attribute=None, unit='unit', rid='rid'),
            mock.call(attribute=None, unit='unit', rid='rid')])

        mock_relation_get.reset_mock()
        for rdata in utils.container_scoped_relation_get(attribute='attr'):
            pass
        mock_relation_get.assert_has_calls([
            mock.call(attribute='attr', unit='unit', rid='rid'),
            mock.call(attribute='attr', unit='unit', rid='rid')])

    @mock.patch.object(utils, 'container_scoped_relation_get')
    def test_get_subordinate_release_packages(
            self,
            mock_container_scoped_relation_get):
        rdata = {
            'queens': {'snap': {'install': ['q_inst'], 'purge': ['q_purg']}},
            'stein': {'deb': {'install': ['s_inst'], 'purge': ['s_purg']}}}
        mock_container_scoped_relation_get.return_value = [
            json.dumps(rdata),
            json.dumps(rdata),
        ]
        # None of the subordinate relations have information about rocky or
        # earlier for deb installations
        self.assertEquals(
            utils.get_subordinate_release_packages('rocky'),
            utils.SubordinatePackages(set(), set()))
        # Information on most recent earlier release with matching package
        # type will be provided when requesting a release not specifically
        # provided by subordinates
        self.assertEquals(
            utils.get_subordinate_release_packages(
                'rocky', package_type='snap'),
            utils.SubordinatePackages(
                {'q_inst'}, {'q_purg'}))
        self.assertEquals(
            utils.get_subordinate_release_packages('train'),
            utils.SubordinatePackages(
                {'s_inst'}, {'s_purg'}))
        # Confirm operation when each subordinate has different release package
        # information
        rdata2 = copy.deepcopy(rdata)
        rdata2.update({
            'train': {'deb': {'install': ['t_inst'], 'purge': ['t_purg']}}})
        mock_container_scoped_relation_get.return_value = [
            json.dumps(rdata),
            json.dumps(rdata2),
        ]
        self.assertEquals(
            utils.get_subordinate_release_packages('train'),
            utils.SubordinatePackages(
                {'s_inst', 't_inst'}, {'s_purg', 't_purg'}))
        # Confirm operation when one of the subordinate relations does not
        # implement sharing the package information
        mock_container_scoped_relation_get.return_value = [
            json.dumps(rdata),
            None,
        ]
        self.assertEquals(
            utils.get_subordinate_release_packages('train'),
            utils.SubordinatePackages(
                {'s_inst'}, {'s_purg'}))
