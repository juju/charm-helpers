from mock import patch, call, mock_open

import collections
import six
import errno
from shutil import rmtree
from tempfile import mkdtemp
from threading import Timer
from testtools import TestCase
import json
import copy
import shutil

import charmhelpers.contrib.storage.linux.ceph as ceph_utils

from charmhelpers.core.unitdata import Storage
from subprocess import CalledProcessError
from tests.helpers import patch_open, FakeRelation
import nose.plugins.attrib
import os
import time

LS_POOLS = b"""
.rgw.foo
images
volumes
rbd
"""

LS_RBDS = b"""
rbd1
rbd2
rbd3
"""

IMG_MAP = b"""
bar
baz
"""
# Vastly abbreviated output from ceph osd dump --format=json
OSD_DUMP = b"""
{
    "pools": [
        {
            "pool": 2,
            "pool_name": "rbd",
            "flags": 1,
            "flags_names": "hashpspool",
            "type": 1,
            "size": 3,
            "min_size": 2,
            "crush_ruleset": 0,
            "object_hash": 2,
            "pg_num": 64,
            "pg_placement_num": 64,
            "crash_replay_interval": 0,
            "last_change": "1",
            "last_force_op_resend": "0",
            "auid": 0,
            "snap_mode": "selfmanaged",
            "snap_seq": 0,
            "snap_epoch": 0,
            "pool_snaps": [],
            "removed_snaps": "[]",
            "quota_max_bytes": 0,
            "quota_max_objects": 0,
            "tiers": [],
            "tier_of": -1,
            "read_tier": -1,
            "write_tier": -1,
            "cache_mode": "writeback",
            "target_max_bytes": 0,
            "target_max_objects": 0,
            "cache_target_dirty_ratio_micro": 0,
            "cache_target_full_ratio_micro": 0,
            "cache_min_flush_age": 0,
            "cache_min_evict_age": 0,
            "erasure_code_profile": "",
            "hit_set_params": {
                "type": "none"
            },
            "hit_set_period": 0,
            "hit_set_count": 0,
            "stripe_width": 0
        }
    ]
}
"""

MONMAP_DUMP = b"""{
    "name": "ip-172-31-13-119", "rank": 0, "state": "leader",
    "election_epoch": 18, "quorum": [0, 1, 2],
    "outside_quorum": [],
    "extra_probe_peers": [],
    "sync_provider": [],
    "monmap": {
        "epoch": 1,
        "fsid": "9fdc313c-db30-11e5-9805-0242fda74275",
        "modified": "0.000000",
        "created": "0.000000",
        "mons": [
            {
                "rank": 0,
                "name": "ip-172-31-13-119",
                "addr": "172.31.13.119:6789\\/0"},
            {
                "rank": 1,
                "name": "ip-172-31-24-50",
                "addr": "172.31.24.50:6789\\/0"},
            {
                "rank": 2,
                "name": "ip-172-31-33-107",
                "addr": "172.31.33.107:6789\\/0"}
        ]}}"""

CEPH_CLIENT_RELATION = {
    'ceph:8': {
        'ceph/0': {
            'auth': 'cephx',
            'broker-rsp-glance-0': '{"request-id": "0bc7dc54", "exit-code": 0}',
            'broker-rsp-glance-1': '{"request-id": "0880e22a", "exit-code": 0}',
            'broker-rsp-glance-2': '{"request-id": "0da543b8", "exit-code": 0}',
            'broker_rsp': '{"request-id": "0da543b8", "exit-code": 0}',
            'ceph-public-address': '10.5.44.103',
            'key': 'AQCLDttVuHXINhAAvI144CB09dYchhHyTUY9BQ==',
            'private-address': '10.5.44.103',
        },
        'ceph/1': {
            'auth': 'cephx',
            'ceph-public-address': '10.5.44.104',
            'key': 'AQCLDttVuHXINhAAvI144CB09dYchhHyTUY9BQ==',
            'private-address': '10.5.44.104',
        },
        'ceph/2': {
            'auth': 'cephx',
            'ceph-public-address': '10.5.44.105',
            'key': 'AQCLDttVuHXINhAAvI144CB09dYchhHyTUY9BQ==',
            'private-address': '10.5.44.105',
        },
        'glance/0': {
            'broker_req': '{"api-version": 1, "request-id": "0bc7dc54", "ops": [{"replicas": 3, "name": "glance", "op": "create-pool", "rbd-mirroring-mode": "pool"}]}',
            'private-address': '10.5.44.109',
        },
    }
}

CEPH_CLIENT_RELATION_LEGACY = copy.deepcopy(CEPH_CLIENT_RELATION)
CEPH_CLIENT_RELATION_LEGACY['ceph:8']['ceph/0'] = {
    'auth': 'cephx',
    'broker_rsp': '{"exit-code": 0}',
    'ceph-public-address': '10.5.44.103',
    'key': 'AQCLDttVuHXINhAAvI144CB09dYchhHyTUY9BQ==',
    'private-address': '10.5.44.103',
}


class TestConfig():

    def __init__(self):
        self.config = {}

    def set(self, key, value):
        self.config[key] = value

    def get(self, key):
        return self.config.get(key)


class CephBasicUtilsTests(TestCase):
    def setUp(self):
        super(CephBasicUtilsTests, self).setUp()
        [self._patch(m) for m in [
            'check_output',
        ]]

    def _patch(self, method):
        _m = patch.object(ceph_utils, method)
        mock = _m.start()
        self.addCleanup(_m.stop)
        setattr(self, method, mock)

    def test_enabled_manager_modules(self):
        self.check_output.return_value = b'{"enabled_modules": []}'
        ceph_utils.enabled_manager_modules()
        self.check_output.assert_called_once_with(['ceph', 'mgr', 'module', 'ls'])


class CephUtilsTests(TestCase):
    def setUp(self):
        super(CephUtilsTests, self).setUp()
        [self._patch(m) for m in [
            'check_call',
            'check_output',
            'config',
            'relation_get',
            'related_units',
            'relation_ids',
            'relation_set',
            'log',
            'cmp_pkgrevno',
            'enabled_manager_modules',
        ]]
        # Ensure the config is setup for mocking properly.
        self.test_config = TestConfig()
        self.config.side_effect = self.test_config.get
        self.cmp_pkgrevno.return_value = 1
        self.enabled_manager_modules.return_value = []

    def _patch(self, method):
        _m = patch.object(ceph_utils, method)
        mock = _m.start()
        self.addCleanup(_m.stop)
        setattr(self, method, mock)

    def _get_osd_settings_test_helper(self, settings, expected=None):
        units = {
            'client:1': ['ceph-iscsi/1', 'ceph-iscsi/2'],
            'client:3': ['cinder-ceph/0', 'cinder-ceph/3']}
        self.relation_ids.return_value = units.keys()
        self.related_units.side_effect = lambda x: units[x]
        self.relation_get.side_effect = lambda x, y, z: settings[y]
        if expected:
            self.assertEqual(
                ceph_utils.get_osd_settings('client'),
                expected)
        else:
            ceph_utils.get_osd_settings('client'),

    def test_get_osd_settings_all_unset(self):
        settings = {
            'ceph-iscsi/1': None,
            'ceph-iscsi/2': None,
            'cinder-ceph/0': None,
            'cinder-ceph/3': None}
        self._get_osd_settings_test_helper(settings, {})

    def test_get_osd_settings_one_group_set(self):
        settings = {
            'ceph-iscsi/1': '{"osd heartbeat grace": 5}',
            'ceph-iscsi/2': '{"osd heartbeat grace": 5}',
            'cinder-ceph/0': '{"osd heartbeat interval": 25}',
            'cinder-ceph/3': '{"osd heartbeat interval": 25}'}
        self._get_osd_settings_test_helper(
            settings,
            {'osd heartbeat interval': 25,
             'osd heartbeat grace': 5})

    def test_get_osd_settings_invalid_option(self):
        settings = {
            'ceph-iscsi/1': '{"osd foobar": 5}',
            'ceph-iscsi/2': None,
            'cinder-ceph/0': None,
            'cinder-ceph/3': None}
        self.assertRaises(
            ceph_utils.OSDSettingNotAllowed,
            self._get_osd_settings_test_helper,
            settings)

    def test_get_osd_settings_conflicting_options(self):
        settings = {
            'ceph-iscsi/1': '{"osd heartbeat grace": 5}',
            'ceph-iscsi/2': None,
            'cinder-ceph/0': '{"osd heartbeat grace": 6}',
            'cinder-ceph/3': None}
        self.assertRaises(
            ceph_utils.OSDSettingConflict,
            self._get_osd_settings_test_helper,
            settings)

    @patch.object(ceph_utils, 'application_name')
    def test_send_application_name(self, application_name):
        application_name.return_value = 'client'
        ceph_utils.send_application_name()
        self.relation_set.assert_called_once_with(
            relation_settings={'application-name': 'client'},
            relation_id=None)
        self.relation_set.reset_mock()
        ceph_utils.send_application_name(relid='rid:1')
        self.relation_set.assert_called_once_with(
            relation_settings={'application-name': 'client'},
            relation_id='rid:1')

    @patch.object(ceph_utils, 'get_osd_settings')
    def test_send_osd_settings(self, _get_osd_settings):
        self.relation_ids.return_value = ['client:1', 'client:3']
        _get_osd_settings.return_value = {
            'osd heartbeat grace': 5,
            'osd heartbeat interval': 25}
        ceph_utils.send_osd_settings()
        expected_calls = [
            call(
                relation_id='client:1',
                relation_settings={
                    'osd-settings': ('{"osd heartbeat grace": 5, '
                                     '"osd heartbeat interval": 25}')}),
            call(
                relation_id='client:3',
                relation_settings={
                    'osd-settings': ('{"osd heartbeat grace": 5, '
                                     '"osd heartbeat interval": 25}')})]
        self.relation_set.assert_has_calls(expected_calls, any_order=True)

    @patch.object(ceph_utils, 'get_osd_settings')
    def test_send_osd_settings_bad_settings(self, _get_osd_settings):
        _get_osd_settings.side_effect = ceph_utils.OSDSettingConflict()
        ceph_utils.send_osd_settings()
        self.assertFalse(self.relation_set.called)

    def test_validator_valid(self):
        # 1 is an int
        ceph_utils.validator(value=1,
                             valid_type=int)

    def test_validator_valid_range(self):
        # 1 is an int between 0 and 2
        ceph_utils.validator(value=1,
                             valid_type=int,
                             valid_range=[0, 2])

    def test_validator_invalid_range(self):
        # 1 is an int that isn't in the valid list of only 0
        self.assertRaises(ValueError, ceph_utils.validator,
                          value=1,
                          valid_type=int,
                          valid_range=[0])

    def test_validator_invalid_string_list(self):
        # foo is a six.string_types that isn't in the valid string list
        self.assertRaises(AssertionError, ceph_utils.validator,
                          value="foo",
                          valid_type=six.string_types,
                          valid_range=["valid", "list", "of", "strings"])

    def test_validator_valid_string(self):
        ceph_utils.validator(value="foo",
                             valid_type=six.string_types,
                             valid_range=["foo"])

    def test_validator_valid_string_type(self):
        ceph_utils.validator(value="foo",
                             valid_type=str,
                             valid_range=["foo"])

    def test_pool_set_quota(self):
        p = ceph_utils.BasePool(service='admin', op={
            'name': 'fake-pool',
            'max-bytes': 'fake-byte-quota',
        })
        p.set_quota()
        self.check_call.assert_called_once_with([
            'ceph', '--id', 'admin', 'osd',
            'pool', 'set-quota', 'fake-pool', 'max_bytes', 'fake-byte-quota'])
        self.check_call.reset_mock()
        p = ceph_utils.BasePool(service='admin', op={
            'name': 'fake-pool',
            'max-objects': 'fake-object-count-quota',
        })
        p.set_quota()
        self.check_call.assert_called_once_with([
            'ceph', '--id', 'admin', 'osd',
            'pool', 'set-quota', 'fake-pool', 'max_objects',
            'fake-object-count-quota'])
        self.check_call.reset_mock()
        p = ceph_utils.BasePool(service='admin', op={
            'name': 'fake-pool',
            'max-bytes': 'fake-byte-quota',
            'max-objects': 'fake-object-count-quota',
        })
        p.set_quota()
        self.check_call.assert_called_once_with([
            'ceph', '--id', 'admin', 'osd',
            'pool', 'set-quota', 'fake-pool', 'max_bytes', 'fake-byte-quota',
            'max_objects', 'fake-object-count-quota'])

    def test_pool_set_compression(self):
        p = ceph_utils.BasePool(service='admin', op={
            'name': 'fake-pool',
            'compression-algorithm': 'lz4',
        })
        p.set_compression()
        self.check_call.assert_called_once_with([
            'ceph', '--id', 'admin', 'osd', 'pool', 'set', 'fake-pool',
            'compression_algorithm', 'lz4'])
        self.check_call.reset_mock()
        p = ceph_utils.BasePool(service='admin', op={
            'name': 'fake-pool',
            'compression-algorithm': 'lz4',
            'compression-mode': 'fake-mode',
            'compression-required-ratio': 'fake-ratio',
            'compression-min-blob-size': 'fake-min-blob-size',
            'compression-min-blob-size-hdd': 'fake-min-blob-size-hdd',
            'compression-min-blob-size-ssd': 'fake-min-blob-size-ssd',
            'compression-max-blob-size': 'fake-max-blob-size',
            'compression-max-blob-size-hdd': 'fake-max-blob-size-hdd',
            'compression-max-blob-size-ssd': 'fake-max-blob-size-ssd',
        })
        p.set_compression()
        self.check_call.assert_has_calls([
            call(['ceph', '--id', 'admin', 'osd', 'pool', 'set', 'fake-pool',
                  'compression_algorithm', 'lz4']),
            call(['ceph', '--id', 'admin', 'osd', 'pool', 'set', 'fake-pool',
                  'compression_mode', 'fake-mode']),
            call(['ceph', '--id', 'admin', 'osd', 'pool', 'set', 'fake-pool',
                  'compression_required_ratio', 'fake-ratio']),
            call(['ceph', '--id', 'admin', 'osd', 'pool', 'set', 'fake-pool',
                  'compression_min_blob_size', 'fake-min-blob-size']),
            call(['ceph', '--id', 'admin', 'osd', 'pool', 'set', 'fake-pool',
                  'compression_min_blob_size_hdd', 'fake-min-blob-size-hdd']),
            call(['ceph', '--id', 'admin', 'osd', 'pool', 'set', 'fake-pool',
                  'compression_min_blob_size_ssd', 'fake-min-blob-size-ssd']),
            call(['ceph', '--id', 'admin', 'osd', 'pool', 'set', 'fake-pool',
                  'compression_max_blob_size', 'fake-max-blob-size']),
            call(['ceph', '--id', 'admin', 'osd', 'pool', 'set', 'fake-pool',
                  'compression_max_blob_size_hdd', 'fake-max-blob-size-hdd']),
            call(['ceph', '--id', 'admin', 'osd', 'pool', 'set', 'fake-pool',
                  'compression_max_blob_size_ssd', 'fake-max-blob-size-ssd']),
        ], any_order=True)

    def test_pool_add_cache_tier(self):
        p = ceph_utils.Pool(name='test', service='admin')
        p.add_cache_tier('cacher', 'readonly')
        self.check_call.assert_has_calls([
            call(['ceph', '--id', 'admin', 'osd', 'tier', 'add', 'test', 'cacher']),
            call(['ceph', '--id', 'admin', 'osd', 'tier', 'cache-mode', 'cacher', 'readonly']),
            call(['ceph', '--id', 'admin', 'osd', 'tier', 'set-overlay', 'test', 'cacher']),
            call(['ceph', '--id', 'admin', 'osd', 'pool', 'set', 'cacher', 'hit_set_type', 'bloom']),
        ])

    @patch.object(ceph_utils, 'get_cache_mode')
    def test_pool_remove_readonly_cache_tier(self, cache_mode):
        cache_mode.return_value = 'readonly'

        p = ceph_utils.Pool(name='test', service='admin')
        p.remove_cache_tier(cache_pool='cacher')
        self.check_call.assert_has_calls([
            call(['ceph', '--id', 'admin', 'osd', 'tier', 'cache-mode', 'cacher', 'none']),
            call(['ceph', '--id', 'admin', 'osd', 'tier', 'remove', 'test', 'cacher']),
        ])

    @patch.object(ceph_utils, 'get_cache_mode')
    def test_pool_remove_writeback_cache_tier(self, cache_mode):
        cache_mode.return_value = 'writeback'
        self.cmp_pkgrevno.return_value = 1

        p = ceph_utils.Pool(name='test', service='admin')
        p.remove_cache_tier(cache_pool='cacher')
        self.check_call.assert_has_calls([
            call(['ceph', '--id', 'admin', 'osd', 'tier', 'cache-mode', 'cacher', 'forward',
                  '--yes-i-really-mean-it']),
            call(['rados', '--id', 'admin', '-p', 'cacher', 'cache-flush-evict-all']),
            call(['ceph', '--id', 'admin', 'osd', 'tier', 'remove-overlay', 'test']),
            call(['ceph', '--id', 'admin', 'osd', 'tier', 'remove', 'test', 'cacher']),
        ])

    @patch.object(ceph_utils, 'get_osds')
    def test_get_pg_num_pg_calc_values(self, get_osds):
        """Tests the calculated pg num in the normal case works"""
        # Check the growth case ... e.g. 200 PGs per OSD if the cluster is
        # expected to grown in the near future.
        get_osds.return_value = range(1, 11)
        self.test_config.set('pgs-per-osd', 200)
        p = ceph_utils.Pool(name='test', service='admin')

        # For Pool Size of 3, 200 PGs/OSD, and 40% of the overall data,
        # the pg num should be 256
        pg_num = p.get_pgs(pool_size=3, percent_data=40)
        self.assertEqual(256, pg_num)

        self.test_config.set('pgs-per-osd', 300)
        pg_num = p.get_pgs(pool_size=3, percent_data=100)
        self.assertEquals(1024, pg_num)

        # Tests the case in which the expected OSD count is provided (and is
        # greater than the found OSD count).
        self.test_config.set('pgs-per-osd', 100)
        self.test_config.set('expected-osd-count', 20)
        pg_num = p.get_pgs(pool_size=3, percent_data=100)
        self.assertEquals(512, pg_num)

        # Test small % weight with minimal OSD count (3)
        get_osds.return_value = range(1, 3)
        self.test_config.set('expected-osd-count', None)
        self.test_config.set('pgs-per-osd', None)
        pg_num = p.get_pgs(pool_size=3, percent_data=0.1)
        self.assertEquals(2, pg_num)

        # Check device_class is passed to get_osds
        p.get_pgs(pool_size=3, percent_data=90, device_class='nvme')
        get_osds.assert_called_with('admin', 'nvme')

    @patch.object(ceph_utils, 'get_osds')
    def test_replicated_pool_create_old_ceph(self, get_osds):
        self.cmp_pkgrevno.return_value = -1
        get_osds.return_value = None
        p = ceph_utils.ReplicatedPool(name='test', service='admin', replicas=3)
        p.create()

        self.check_call.assert_has_calls([
            call(['ceph', '--id', 'admin', 'osd', 'pool', 'create', 'test', str(200)]),
            call(['ceph', '--id', 'admin', 'osd', 'pool', 'set', 'test', 'size', str(3)]),
        ])
        self.assertEqual(self.check_call.call_count, 2)

    @patch.object(ceph_utils, 'get_osds')
    def test_replicated_pool_create_luminous_ceph(self, get_osds):
        self.cmp_pkgrevno.side_effect = [-1, 1]
        get_osds.return_value = None
        p = ceph_utils.ReplicatedPool(name='test', service='admin', replicas=3)
        p.create()

        self.check_call.assert_has_calls([
            call(['ceph', '--id', 'admin', 'osd',
                  'pool', 'create', 'test', str(200)]),
            call(['ceph', '--id', 'admin', 'osd',
                  'pool', 'set', 'test', 'size', str(3)]),
            call(['ceph', '--id', 'admin', 'osd', 'pool',
                  'application', 'enable', 'test', 'unknown'])
        ])
        self.assertEqual(self.check_call.call_count, 3)

    @patch.object(ceph_utils, 'get_osds')
    def test_replicated_pool_create_small_osds(self, get_osds):
        get_osds.return_value = range(1, 5)
        self.cmp_pkgrevno.return_value = -1
        p = ceph_utils.ReplicatedPool(name='test', service='admin', replicas=3,
                                      percent_data=10)
        p.create()

        # Using the PG Calc, for 4 OSDs with a size of 3 and 10% of the data
        # at 100 PGs/OSD, the number of expected placement groups will be 16
        self.check_call.assert_has_calls([
            call(['ceph', '--id', 'admin', 'osd', 'pool', 'create', 'test',
                  '16']),
        ])

    @patch.object(ceph_utils, 'get_osds')
    def test_replicated_pool_create_medium_osds(self, get_osds):
        self.cmp_pkgrevno.return_value = -1
        get_osds.return_value = range(1, 9)
        p = ceph_utils.ReplicatedPool(name='test', service='admin', replicas=3,
                                      percent_data=50)
        p.create()

        # Using the PG Calc, for 8 OSDs with a size of 3 and 50% of the data
        # at 100 PGs/OSD, the number of expected placement groups will be 128
        self.check_call.assert_has_calls([
            call(['ceph', '--id', 'admin', 'osd', 'pool', 'create', 'test',
                  '128']),
            call(['ceph', '--id', 'admin', 'osd', 'pool', 'set', 'test', 'size', '3']),
        ])

    @patch.object(ceph_utils, 'get_osds')
    def test_replicated_pool_create_autoscaler(self, get_osds):
        self.enabled_manager_modules.return_value = ['pg_autoscaler']
        self.cmp_pkgrevno.return_value = 1
        get_osds.return_value = range(1, 9)
        p = ceph_utils.ReplicatedPool(name='test', service='admin', replicas=3,
                                      percent_data=50)
        p.create()
        # Using the PG Calc, for 8 OSDs with a size of 3 and 50% of the data

        # at 100 PGs/OSD, the number of expected placement groups will be 128
        self.check_call.assert_has_calls([
            call(['ceph', '--id', 'admin', 'osd', 'pool',
                  'create', '--pg-num-min=32', 'test', '128']),
            call(['ceph', '--id', 'admin', 'osd', 'pool',
                  'set', 'test', 'size', '3']),
            call(['ceph', '--id', 'admin', 'osd', 'pool',
                  'set', 'test', 'target_size_ratio', '0.5']),
            call(['ceph', '--id', 'admin', 'osd', 'pool',
                  'application', 'enable', 'test', 'unknown']),
            call(['ceph', '--id', 'admin', 'osd', 'pool',
                  'set', 'test', 'pg_autoscale_mode', 'on'])
        ])

    @patch.object(ceph_utils, 'get_osds')
    def test_replicated_pool_create_autoscaler_small(self, get_osds):
        self.enabled_manager_modules.return_value = ['pg_autoscaler']
        self.cmp_pkgrevno.return_value = 1
        get_osds.return_value = range(1, 3)
        p = ceph_utils.ReplicatedPool(name='test', service='admin', replicas=3,
                                      percent_data=1)
        p.create()
        # Using the PG Calc, for 8 OSDs with a size of 3 and 50% of the data

        # at 100 PGs/OSD, the number of expected placement groups will be 128
        self.check_call.assert_has_calls([
            call(['ceph', '--id', 'admin', 'osd', 'pool',
                  'create', '--pg-num-min=2', 'test', '2']),
            call(['ceph', '--id', 'admin', 'osd', 'pool',
                  'set', 'test', 'size', '3']),
            call(['ceph', '--id', 'admin', 'osd', 'pool',
                  'set', 'test', 'target_size_ratio', '0.01']),
            call(['ceph', '--id', 'admin', 'osd', 'pool',
                  'application', 'enable', 'test', 'unknown']),
            call(['ceph', '--id', 'admin', 'osd', 'pool',
                  'set', 'test', 'pg_autoscale_mode', 'on'])
        ])

    @patch.object(ceph_utils, 'get_osds')
    def test_replicated_pool_create_large_osds(self, get_osds):
        get_osds.return_value = range(1, 41)
        self.cmp_pkgrevno.return_value = -1
        p = ceph_utils.ReplicatedPool(name='test', service='admin', replicas=3,
                                      percent_data=100)
        p.create()

        # Using the PG Calc, for 40 OSDs with a size of 3 and 100% of the
        # data at 100 PGs/OSD then the number of expected placement groups
        # will be 1024.
        self.check_call.assert_has_calls([
            call(['ceph', '--id', 'admin', 'osd', 'pool', 'create', 'test',
                  '1024']),
        ])

    @patch.object(ceph_utils, 'get_osds')
    def test_replicated_pool_create_xlarge_osds(self, get_osds):
        get_osds.return_value = range(1, 1001)
        self.cmp_pkgrevno.return_value = -1
        p = ceph_utils.ReplicatedPool(name='test', service='admin', replicas=3,
                                      percent_data=100)
        p.create()

        # Using the PG Calc, for 1,000 OSDs with a size of 3 and 100% of the
        # data at 100 PGs/OSD then the number of expected placement groups
        # will be 32768
        self.check_call.assert_has_calls([
            call(['ceph', '--id', 'admin', 'osd', 'pool', 'create', 'test',
                  '32768']),
        ])

    @patch.object(ceph_utils, 'get_osds')
    def test_replicated_pool_create_failed(self, get_osds):
        get_osds.return_value = range(1, 1001)
        self.check_call.side_effect = CalledProcessError(returncode=1,
                                                         cmd='mock',
                                                         output=None)
        p = ceph_utils.ReplicatedPool(name='test', service='admin', replicas=3)
        self.assertRaises(CalledProcessError, p.create)

    @patch.object(ceph_utils, 'get_osds')
    @patch.object(ceph_utils, 'pool_exists')
    def test_replicated_pool_skips_creation(self, pool_exists, get_osds):
        get_osds.return_value = range(1, 1001)
        pool_exists.return_value = True
        p = ceph_utils.ReplicatedPool(name='test', service='admin', replicas=3)
        p.create()
        self.check_call.assert_has_calls([])

    def test_erasure_pool_create_failed(self):
        self.check_output.side_effect = CalledProcessError(returncode=1,
                                                           cmd='ceph',
                                                           output=None)
        p = ceph_utils.ErasurePool('test', 'admin', 'foo')
        self.assertRaises(ceph_utils.PoolCreationError, p.create)

    @patch.object(ceph_utils, 'get_erasure_profile')
    @patch.object(ceph_utils, 'get_osds')
    def test_erasure_pool_create(self, get_osds, erasure_profile):
        self.cmp_pkgrevno.return_value = 1
        get_osds.return_value = range(1, 60)
        erasure_profile.return_value = {
            'directory': '/usr/lib/x86_64-linux-gnu/ceph/erasure-code',
            'k': '2',
            'technique': 'reed_sol_van',
            'm': '1',
            'plugin': 'jerasure'}
        p = ceph_utils.ErasurePool(name='test', service='admin',
                                   percent_data=100)
        p.create()
        self.check_call.assert_has_calls([
            call(['ceph', '--id', 'admin', 'osd', 'pool', 'create',
                  '--pg-num-min=32', 'test',
                  '2048', '2048', 'erasure', 'default']),
            call(['ceph', '--id', 'admin', 'osd', 'pool',
                  'set', 'test', 'target_size_ratio', '1.0']),
            call(['ceph', '--id', 'admin', 'osd', 'pool',
                  'application', 'enable', 'test', 'unknown'])
        ])

    @patch.object(ceph_utils, 'get_erasure_profile')
    @patch.object(ceph_utils, 'get_osds')
    def test_erasure_pool_create_autoscaler(self,
                                            get_osds,
                                            erasure_profile):
        self.enabled_manager_modules.return_value = ['pg_autoscaler']
        self.cmp_pkgrevno.return_value = 1
        get_osds.return_value = range(1, 60)
        erasure_profile.return_value = {
            'directory': '/usr/lib/x86_64-linux-gnu/ceph/erasure-code',
            'k': '2',
            'technique': 'reed_sol_van',
            'm': '1',
            'plugin': 'jerasure'}
        p = ceph_utils.ErasurePool(name='test', service='admin',
                                   percent_data=100, allow_ec_overwrites=True)
        p.create()
        self.check_call.assert_has_calls([
            call(['ceph', '--id', 'admin', 'osd', 'pool',
                  'create', '--pg-num-min=32', 'test',
                  '2048', '2048', 'erasure', 'default']),
            call(['ceph', '--id', 'admin', 'osd', 'pool',
                  'set', 'test', 'target_size_ratio', '1.0']),
            call(['ceph', '--id', 'admin', 'osd', 'pool',
                  'application', 'enable', 'test', 'unknown']),
            call(['ceph', '--id', 'admin', 'osd', 'pool',
                  'set', 'test', 'pg_autoscale_mode', 'on']),
            call(['ceph', '--id', 'admin', 'osd', 'pool',
                  'set', 'test', 'allow_ec_overwrites', 'true']),
        ])

    def test_get_erasure_profile_none(self):
        self.check_output.side_effect = CalledProcessError(1, 'ceph')
        return_value = ceph_utils.get_erasure_profile('admin', 'unknown')
        self.assertEqual(None, return_value)

    def test_pool_set_int(self):
        self.check_call.return_value = 0
        ceph_utils.pool_set(service='admin', pool_name='data', key='test', value=2)
        self.check_call.assert_has_calls([
            call(['ceph', '--id', 'admin', 'osd', 'pool', 'set', 'data', 'test', '2'])
        ])

    def test_pool_set_bool(self):
        self.check_call.return_value = 0
        ceph_utils.pool_set(service='admin', pool_name='data', key='test', value=True)
        self.check_call.assert_has_calls([
            call(['ceph', '--id', 'admin', 'osd', 'pool', 'set', 'data', 'test', 'true'])
        ])

    def test_pool_set_str(self):
        self.check_call.return_value = 0
        ceph_utils.pool_set(service='admin', pool_name='data', key='test', value='two')
        self.check_call.assert_has_calls([
            call(['ceph', '--id', 'admin', 'osd', 'pool', 'set', 'data', 'test', 'two'])
        ])

    def test_pool_set_fails(self):
        self.check_call.side_effect = CalledProcessError(returncode=1, cmd='mock',
                                                         output=None)
        self.assertRaises(CalledProcessError, ceph_utils.pool_set,
                          service='admin', pool_name='data', key='test', value=2)

    def test_snapshot_pool(self):
        self.check_call.return_value = 0
        ceph_utils.snapshot_pool(service='admin', pool_name='data', snapshot_name='test-snap-1')
        self.check_call.assert_has_calls([
            call(['ceph', '--id', 'admin', 'osd', 'pool', 'mksnap', 'data', 'test-snap-1'])
        ])

    def test_snapshot_pool_fails(self):
        self.check_call.side_effect = CalledProcessError(returncode=1, cmd='mock',
                                                         output=None)
        self.assertRaises(CalledProcessError, ceph_utils.snapshot_pool,
                          service='admin', pool_name='data', snapshot_name='test-snap-1')

    def test_remove_pool_snapshot(self):
        self.check_call.return_value = 0
        ceph_utils.remove_pool_snapshot(service='admin', pool_name='data', snapshot_name='test-snap-1')
        self.check_call.assert_has_calls([
            call(['ceph', '--id', 'admin', 'osd', 'pool', 'rmsnap', 'data', 'test-snap-1'])
        ])

    def test_set_pool_quota(self):
        self.check_call.return_value = 0
        ceph_utils.set_pool_quota(service='admin', pool_name='data',
                                  max_bytes=1024)
        self.check_call.assert_has_calls([
            call(['ceph', '--id', 'admin', 'osd', 'pool', 'set-quota', 'data',
                  'max_bytes', '1024'])
        ])
        ceph_utils.set_pool_quota(service='admin', pool_name='data',
                                  max_objects=1024)
        self.check_call.assert_has_calls([
            call(['ceph', '--id', 'admin', 'osd', 'pool', 'set-quota', 'data',
                  'max_objects', '1024'])
        ])
        ceph_utils.set_pool_quota(service='admin', pool_name='data',
                                  max_bytes=1024, max_objects=1024)
        self.check_call.assert_has_calls([
            call(['ceph', '--id', 'admin', 'osd', 'pool', 'set-quota', 'data',
                  'max_bytes', '1024', 'max_objects', '1024'])
        ])

    def test_remove_pool_quota(self):
        self.check_call.return_value = 0
        ceph_utils.remove_pool_quota(service='admin', pool_name='data')
        self.check_call.assert_has_calls([
            call(['ceph', '--id', 'admin', 'osd', 'pool', 'set-quota', 'data', 'max_bytes', '0'])
        ])

    @patch.object(ceph_utils, 'erasure_profile_exists')
    def test_create_erasure_profile(self, existing_profile):
        existing_profile.return_value = False
        self.test_config.set('customize-failure-domain', False)
        self.cmp_pkgrevno.return_value = -1
        ceph_utils.create_erasure_profile(
            service='admin', profile_name='super-profile', erasure_plugin_name='jerasure',
            failure_domain='rack', data_chunks=10, coding_chunks=3,
            device_class='ssd')

        cmd = ['ceph', '--id', 'admin', 'osd', 'erasure-code-profile', 'set', 'super-profile',
               'plugin=' + 'jerasure', 'k=' + str(10), 'm=' + str(3),
               'ruleset-failure-domain=' + 'rack']
        self.check_call.assert_has_calls([call(cmd)])

        self.cmp_pkgrevno.return_value = 1
        ceph_utils.create_erasure_profile(
            service='admin', profile_name='super-profile', erasure_plugin_name='jerasure',
            failure_domain='rack', data_chunks=10, coding_chunks=3,
            device_class='ssd')

        cmd = ['ceph', '--id', 'admin', 'osd', 'erasure-code-profile', 'set', 'super-profile',
               'plugin=' + 'jerasure', 'k=' + str(10), 'm=' + str(3),
               'crush-failure-domain=' + 'rack',
               'crush-device-class=ssd']
        self.check_call.assert_has_calls([call(cmd)])

        existing_profile.return_value = True
        self.check_call.reset_mock()

        ceph_utils.create_erasure_profile(
            service='admin', profile_name='super-profile', erasure_plugin_name='jerasure',
            failure_domain='rack', data_chunks=10, coding_chunks=3,
            device_class='ssd')

        self.check_call.assert_not_called()

    @patch.object(ceph_utils, 'erasure_profile_exists')
    def test_create_erasure_profile_failure_domain(self, existing_profile):
        existing_profile.return_value = False
        self.test_config.set('customize-failure-domain', True)
        self.cmp_pkgrevno.return_value = -1
        ceph_utils.create_erasure_profile(
            service='admin', profile_name='super-profile', erasure_plugin_name='jerasure',
            failure_domain=None, data_chunks=10, coding_chunks=3,
            device_class='ssd')

        cmd = ['ceph', '--id', 'admin', 'osd', 'erasure-code-profile', 'set', 'super-profile',
               'plugin=' + 'jerasure', 'k=' + str(10), 'm=' + str(3),
               'ruleset-failure-domain=' + 'rack']
        self.config.assert_called_once_with('customize-failure-domain')
        self.check_call.assert_has_calls([call(cmd)])

    @patch.object(ceph_utils, 'erasure_profile_exists')
    def test_create_erasure_profile_lrc(self, existing_profile):
        self.cmp_pkgrevno.return_value = -1
        self.test_config.set('customize-failure-domain', False)
        existing_profile.return_value = False
        ceph_utils.create_erasure_profile(
            service='admin', profile_name='super-profile', erasure_plugin_name='lrc',
            failure_domain='host', data_chunks=10, coding_chunks=3, locality=1,
            crush_locality='rack'
        )

        cmd = ['ceph', '--id', 'admin', 'osd', 'erasure-code-profile', 'set', 'super-profile',
               'plugin=' + 'lrc', 'k=' + str(10), 'm=' + str(3),
               'ruleset-failure-domain=' + 'host', 'l=' + str(1),
               'crush-locality=rack']
        self.check_call.assert_has_calls([call(cmd)])

    @patch.object(ceph_utils, 'erasure_profile_exists')
    def test_create_erasure_profile_lrc_no_locality(self, existing_profile):
        self.cmp_pkgrevno.return_value = -1
        self.test_config.set('customize-failure-domain', False)
        existing_profile.return_value = False
        self.assertRaises(
            ValueError,
            ceph_utils.create_erasure_profile,
            service='admin', profile_name='super-profile', erasure_plugin_name='lrc',
            failure_domain='rack', data_chunks=10, coding_chunks=3, locality=None
        )

    @patch.object(ceph_utils, 'erasure_profile_exists')
    def test_create_erasure_profile_invalid_plugin(self, existing_profile):
        self.cmp_pkgrevno.return_value = -1
        self.test_config.set('customize-failure-domain', False)
        existing_profile.return_value = False
        self.assertRaises(
            AssertionError,
            ceph_utils.create_erasure_profile,
            service='admin', profile_name='super-profile', erasure_plugin_name='foobar',
            data_chunks=10, coding_chunks=3
        )

    @patch.object(ceph_utils, 'erasure_profile_exists')
    def test_create_erasure_profile_invalid_technique(self, existing_profile):
        self.cmp_pkgrevno.return_value = -1
        self.test_config.set('customize-failure-domain', False)
        existing_profile.return_value = False
        self.assertRaises(
            AssertionError,
            ceph_utils.create_erasure_profile,
            service='admin', profile_name='super-profile', erasure_plugin_name='jerasure',
            data_chunks=10, coding_chunks=3,
            erasure_plugin_technique='foobar'
        )

    @patch.object(ceph_utils, 'erasure_profile_exists')
    def test_create_erasure_profile_invalid_failure_domain(self, existing_profile):
        self.cmp_pkgrevno.return_value = -1
        self.test_config.set('customize-failure-domain', False)
        existing_profile.return_value = False
        self.assertRaises(
            AssertionError,
            ceph_utils.create_erasure_profile,
            service='admin', profile_name='super-profile', erasure_plugin_name='jerasure',
            data_chunks=10, coding_chunks=3,
            failure_domain='foobar',
        )

    @patch.object(ceph_utils, 'erasure_profile_exists')
    def test_create_erasure_profile_shec(self, existing_profile):
        self.cmp_pkgrevno.return_value = -1
        self.test_config.set('customize-failure-domain', False)
        existing_profile.return_value = False
        ceph_utils.create_erasure_profile(service='admin', profile_name='super-profile', erasure_plugin_name='shec',
                                          failure_domain='rack', data_chunks=10, coding_chunks=3,
                                          durability_estimator=1)

        cmd = ['ceph', '--id', 'admin', 'osd', 'erasure-code-profile', 'set', 'super-profile',
               'plugin=' + 'shec', 'k=' + str(10), 'm=' + str(3),
               'ruleset-failure-domain=' + 'rack', 'c=' + str(1)]
        self.check_call.assert_has_calls([call(cmd)])

    def test_rename_pool(self):
        ceph_utils.rename_pool(service='admin', old_name='old-pool', new_name='new-pool')
        cmd = ['ceph', '--id', 'admin', 'osd', 'pool', 'rename', 'old-pool', 'new-pool']
        self.check_call.assert_called_with(cmd)

    def test_erasure_profile_exists(self):
        self.check_call.return_value = 0
        profile_exists = ceph_utils.erasure_profile_exists(service='admin', name='super-profile')
        cmd = ['ceph', '--id', 'admin',
               'osd', 'erasure-code-profile', 'get',
               'super-profile']
        self.check_call.assert_called_with(cmd)
        self.assertEqual(True, profile_exists)

    def test_set_monitor_key(self):
        cmd = ['ceph', '--id', 'admin',
               'config-key', 'put', 'foo', 'bar']
        ceph_utils.monitor_key_set(service='admin', key='foo', value='bar')
        self.check_output.assert_called_with(cmd)

    def test_get_monitor_key(self):
        cmd = ['ceph', '--id', 'admin',
               'config-key', 'get', 'foo']
        ceph_utils.monitor_key_get(service='admin', key='foo')
        self.check_output.assert_called_with(cmd)

    def test_get_monitor_key_failed(self):
        self.check_output.side_effect = CalledProcessError(
            returncode=2,
            cmd='ceph',
            output='key foo does not exist')
        output = ceph_utils.monitor_key_get(service='admin', key='foo')
        self.assertEqual(None, output)

    def test_monitor_key_exists(self):
        cmd = ['ceph', '--id', 'admin',
               'config-key', 'exists', 'foo']
        ceph_utils.monitor_key_exists(service='admin', key='foo')
        self.check_call.assert_called_with(cmd)

    def test_monitor_key_doesnt_exist(self):
        self.check_call.side_effect = CalledProcessError(
            returncode=2,
            cmd='ceph',
            output='key foo does not exist')
        output = ceph_utils.monitor_key_exists(service='admin', key='foo')
        self.assertEqual(False, output)

    def test_delete_monitor_key(self):
        ceph_utils.monitor_key_delete(service='admin', key='foo')
        cmd = ['ceph', '--id', 'admin',
               'config-key', 'del', 'foo']
        self.check_output.assert_called_with(cmd)

    def test_delete_monitor_key_failed(self):
        self.check_output.side_effect = CalledProcessError(
            returncode=2,
            cmd='ceph',
            output='deletion failed')
        self.assertRaises(CalledProcessError, ceph_utils.monitor_key_delete,
                          service='admin', key='foo')

    def test_get_monmap(self):
        self.check_output.return_value = MONMAP_DUMP
        cmd = ['ceph', '--id', 'admin',
               'mon_status', '--format=json']
        ceph_utils.get_mon_map(service='admin')
        self.check_output.assert_called_with(cmd)

    @patch.object(ceph_utils, 'get_mon_map')
    def test_hash_monitor_names(self, monmap):
        expected_hash_list = [
            '010d57d581604d411b315dd64112bff832ab92c7323fa06077134b50',
            '8e0a9705c1aeafa1ce250cc9f1bb443fc6e5150e5edcbeb6eeb82e3c',
            'c3f8d36ba098c23ee920cb08cfb9beda6b639f8433637c190bdd56ec']
        _monmap_dump = MONMAP_DUMP
        if six.PY3:
            _monmap_dump = _monmap_dump.decode('UTF-8')
        monmap.return_value = json.loads(_monmap_dump)
        hashed_mon_list = ceph_utils.hash_monitor_names(service='admin')
        self.assertEqual(expected=expected_hash_list, observed=hashed_mon_list)

    def test_get_cache_mode(self):
        self.check_output.return_value = OSD_DUMP
        cache_mode = ceph_utils.get_cache_mode(service='admin', pool_name='rbd')
        self.assertEqual("writeback", cache_mode)

    @patch('os.path.exists')
    def test_add_key(self, _exists):
        """It creates a new ceph keyring"""
        _exists.return_value = False
        ceph_utils.add_key('cinder', 'cephkey')
        _cmd = ['ceph-authtool', '/etc/ceph/ceph.client.cinder.keyring',
                '--create-keyring', '--name=client.cinder',
                '--add-key=cephkey']
        self.check_call.assert_called_with(_cmd)

    @patch('os.path.exists')
    def test_add_key_already_exists(self, _exists):
        """It should insert the key into the existing keyring"""
        _exists.return_value = True
        try:
            with patch("__builtin__.open", mock_open(read_data="foo")):
                ceph_utils.add_key('cinder', 'cephkey')
        except ImportError:  # Python3
            with patch("builtins.open", mock_open(read_data="foo")):
                ceph_utils.add_key('cinder', 'cephkey')
        self.assertTrue(self.log.called)
        _cmd = ['ceph-authtool', '/etc/ceph/ceph.client.cinder.keyring',
                '--create-keyring', '--name=client.cinder',
                '--add-key=cephkey']
        self.check_call.assert_called_with(_cmd)

    @patch('os.path.exists')
    def test_add_key_already_exists_and_key_exists(self, _exists):
        """Nothing should happen, apart from a log message"""
        _exists.return_value = True
        try:
            with patch("__builtin__.open", mock_open(read_data="cephkey")):
                ceph_utils.add_key('cinder', 'cephkey')
        except ImportError:  # Python3
            with patch("builtins.open", mock_open(read_data="cephkey")):
                ceph_utils.add_key('cinder', 'cephkey')
        self.assertTrue(self.log.called)
        self.check_call.assert_not_called()

    @patch('os.remove')
    @patch('os.path.exists')
    def test_delete_keyring(self, _exists, _remove):
        """It deletes a ceph keyring."""
        _exists.return_value = True
        ceph_utils.delete_keyring('cinder')
        _remove.assert_called_with('/etc/ceph/ceph.client.cinder.keyring')
        self.assertTrue(self.log.called)

    @patch('os.remove')
    @patch('os.path.exists')
    def test_delete_keyring_not_exists(self, _exists, _remove):
        """It creates a new ceph keyring."""
        _exists.return_value = False
        ceph_utils.delete_keyring('cinder')
        self.assertTrue(self.log.called)
        _remove.assert_not_called()

    @patch('os.path.exists')
    def test_create_keyfile(self, _exists):
        """It creates a new ceph keyfile"""
        _exists.return_value = False
        with patch_open() as (_open, _file):
            ceph_utils.create_key_file('cinder', 'cephkey')
            _file.write.assert_called_with('cephkey')
        self.assertTrue(self.log.called)

    @patch('os.path.exists')
    def test_create_key_file_already_exists(self, _exists):
        """It creates a new ceph keyring"""
        _exists.return_value = True
        ceph_utils.create_key_file('cinder', 'cephkey')
        self.assertTrue(self.log.called)

    @patch('os.mkdir')
    @patch.object(ceph_utils, 'apt_install')
    @patch('os.path.exists')
    def test_install(self, _exists, _install, _mkdir):
        _exists.return_value = False
        ceph_utils.install()
        _mkdir.assert_called_with('/etc/ceph')
        _install.assert_called_with('ceph-common', fatal=True)

    def test_get_osds(self):
        self.check_output.return_value = json.dumps([1, 2, 3]).encode('UTF-8')
        self.assertEquals(ceph_utils.get_osds('test'), [1, 2, 3])

    def test_get_osds_none(self):
        self.check_output.return_value = json.dumps(None).encode('UTF-8')
        self.assertEquals(ceph_utils.get_osds('test'), None)

    def test_get_osds_device_class(self):
        self.check_output.return_value = json.dumps([1, 2, 3]).encode('UTF-8')
        self.assertEquals(ceph_utils.get_osds('test', 'nvme'), [1, 2, 3])
        self.check_output.assert_called_once_with(
            ['ceph', '--id', 'test',
             'osd', 'crush', 'class',
             'ls-osd', 'nvme', '--format=json']
        )

    def test_get_osds_device_class_older(self):
        self.check_output.return_value = json.dumps([1, 2, 3]).encode('UTF-8')
        self.cmp_pkgrevno.return_value = -1
        self.assertEquals(ceph_utils.get_osds('test', 'nvme'), [1, 2, 3])
        self.check_output.assert_called_once_with(
            ['ceph', '--id', 'test', 'osd', 'ls', '--format=json']
        )

    @patch.object(ceph_utils, 'get_osds')
    @patch.object(ceph_utils, 'pool_exists')
    def test_create_pool(self, _exists, _get_osds):
        """It creates rados pool correctly with default replicas """
        _exists.return_value = False
        _get_osds.return_value = [1, 2, 3]
        ceph_utils.create_pool(service='cinder', name='foo')
        self.check_call.assert_has_calls([
            call(['ceph', '--id', 'cinder', 'osd', 'pool',
                  'create', 'foo', '100']),
            call(['ceph', '--id', 'cinder', 'osd', 'pool', 'set',
                  'foo', 'size', '3'])
        ])

    @patch.object(ceph_utils, 'get_osds')
    @patch.object(ceph_utils, 'pool_exists')
    def test_create_pool_2_replicas(self, _exists, _get_osds):
        """It creates rados pool correctly with 3 replicas"""
        _exists.return_value = False
        _get_osds.return_value = [1, 2, 3]
        ceph_utils.create_pool(service='cinder', name='foo', replicas=2)
        self.check_call.assert_has_calls([
            call(['ceph', '--id', 'cinder', 'osd', 'pool',
                  'create', 'foo', '150']),
            call(['ceph', '--id', 'cinder', 'osd', 'pool', 'set',
                  'foo', 'size', '2'])
        ])

    @patch.object(ceph_utils, 'get_osds')
    @patch.object(ceph_utils, 'pool_exists')
    def test_create_pool_argonaut(self, _exists, _get_osds):
        """It creates rados pool correctly with 3 replicas"""
        _exists.return_value = False
        _get_osds.return_value = None
        ceph_utils.create_pool(service='cinder', name='foo')
        self.check_call.assert_has_calls([
            call(['ceph', '--id', 'cinder', 'osd', 'pool',
                  'create', 'foo', '200']),
            call(['ceph', '--id', 'cinder', 'osd', 'pool', 'set',
                  'foo', 'size', '3'])
        ])

    def test_create_pool_already_exists(self):
        self._patch('pool_exists')
        self.pool_exists.return_value = True
        ceph_utils.create_pool(service='cinder', name='foo')
        self.assertTrue(self.log.called)
        self.check_call.assert_not_called()

    def test_keyring_path(self):
        """It correctly derives keyring path from service name"""
        result = ceph_utils._keyring_path('cinder')
        self.assertEquals('/etc/ceph/ceph.client.cinder.keyring', result)

    def test_keyfile_path(self):
        """It correctly derives keyring path from service name"""
        result = ceph_utils._keyfile_path('cinder')
        self.assertEquals('/etc/ceph/ceph.client.cinder.key', result)

    def test_pool_exists(self):
        """It detects an rbd pool exists"""
        self.check_output.return_value = LS_POOLS
        self.assertTrue(ceph_utils.pool_exists('cinder', 'volumes'))
        self.assertTrue(ceph_utils.pool_exists('rgw', '.rgw.foo'))

    def test_pool_does_not_exist(self):
        """It detects an rbd pool exists"""
        self.check_output.return_value = LS_POOLS
        self.assertFalse(ceph_utils.pool_exists('cinder', 'foo'))
        self.assertFalse(ceph_utils.pool_exists('rgw', '.rgw'))

    def test_pool_exists_error(self):
        """ Ensure subprocess errors and sandboxed with False """
        self.check_output.side_effect = CalledProcessError(1, 'rados')
        self.assertFalse(ceph_utils.pool_exists('cinder', 'foo'))

    def test_rbd_exists(self):
        self.check_output.return_value = LS_RBDS
        self.assertTrue(ceph_utils.rbd_exists('service', 'pool', 'rbd1'))
        self.check_output.assert_called_with(
            ['rbd', 'list', '--id', 'service', '--pool', 'pool']
        )

    def test_rbd_does_not_exist(self):
        self.check_output.return_value = LS_RBDS
        self.assertFalse(ceph_utils.rbd_exists('service', 'pool', 'rbd4'))
        self.check_output.assert_called_with(
            ['rbd', 'list', '--id', 'service', '--pool', 'pool']
        )

    def test_rbd_exists_error(self):
        """ Ensure subprocess errors and sandboxed with False """
        self.check_output.side_effect = CalledProcessError(1, 'rbd')
        self.assertFalse(ceph_utils.rbd_exists('cinder', 'foo', 'rbd'))

    def test_create_rbd_image(self):
        ceph_utils.create_rbd_image('service', 'pool', 'image', 128)
        _cmd = ['rbd', 'create', 'image',
                '--size', '128',
                '--id', 'service',
                '--pool', 'pool']
        self.check_call.assert_called_with(_cmd)

    def test_delete_pool(self):
        ceph_utils.delete_pool('cinder', 'pool')
        _cmd = [
            'ceph', '--id', 'cinder',
            'osd', 'pool', 'delete',
            'pool', '--yes-i-really-really-mean-it'
        ]
        self.check_call.assert_called_with(_cmd)

    def test_get_ceph_nodes(self):
        self._patch('relation_ids')
        self._patch('related_units')
        self._patch('relation_get')
        units = ['ceph/1', 'ceph2', 'ceph/3']
        self.relation_ids.return_value = ['ceph:0']
        self.related_units.return_value = units
        self.relation_get.return_value = '192.168.1.1'
        self.assertEquals(len(ceph_utils.get_ceph_nodes()), 3)

    def test_get_ceph_nodes_not_related(self):
        self._patch('relation_ids')
        self.relation_ids.return_value = []
        self.assertEquals(ceph_utils.get_ceph_nodes(), [])

    def test_configure(self):
        self._patch('add_key')
        self._patch('create_key_file')
        self._patch('get_ceph_nodes')
        self._patch('modprobe')
        _hosts = ['192.168.1.1', '192.168.1.2']
        self.get_ceph_nodes.return_value = _hosts
        _conf = ceph_utils.CEPH_CONF.format(
            auth='cephx',
            keyring=ceph_utils._keyring_path('cinder'),
            mon_hosts=",".join(map(str, _hosts)),
            use_syslog='true'
        )
        with patch_open() as (_open, _file):
            ceph_utils.configure('cinder', 'key', 'cephx', 'true')
            _file.write.assert_called_with(_conf)
            _open.assert_called_with('/etc/ceph/ceph.conf', 'w')
        self.modprobe.assert_called_with('rbd')
        self.add_key.assert_called_with('cinder', 'key')
        self.create_key_file.assert_called_with('cinder', 'key')

    def test_image_mapped(self):
        self.check_output.return_value = IMG_MAP
        self.assertTrue(ceph_utils.image_mapped('bar'))

    def test_image_not_mapped(self):
        self.check_output.return_value = IMG_MAP
        self.assertFalse(ceph_utils.image_mapped('foo'))

    def test_image_not_mapped_error(self):
        self.check_output.side_effect = CalledProcessError(1, 'rbd')
        self.assertFalse(ceph_utils.image_mapped('bar'))

    def test_map_block_storage(self):
        _service = 'cinder'
        _pool = 'bar'
        _img = 'foo'
        _cmd = [
            'rbd',
            'map',
            '{}/{}'.format(_pool, _img),
            '--user',
            _service,
            '--secret',
            ceph_utils._keyfile_path(_service),
        ]
        ceph_utils.map_block_storage(_service, _pool, _img)
        self.check_call.assert_called_with(_cmd)

    def test_filesystem_mounted(self):
        self._patch('mounts')
        self.mounts.return_value = [['/afs', '/dev/sdb'], ['/bfs', '/dev/sdd']]
        self.assertTrue(ceph_utils.filesystem_mounted('/afs'))
        self.assertFalse(ceph_utils.filesystem_mounted('/zfs'))

    @patch('os.path.exists')
    def test_make_filesystem(self, _exists):
        _exists.return_value = True
        ceph_utils.make_filesystem('/dev/sdd')
        self.assertTrue(self.log.called)
        self.check_call.assert_called_with(['mkfs', '-t', 'ext4', '/dev/sdd'])

    @patch('os.path.exists')
    def test_make_filesystem_xfs(self, _exists):
        _exists.return_value = True
        ceph_utils.make_filesystem('/dev/sdd', 'xfs')
        self.assertTrue(self.log.called)
        self.check_call.assert_called_with(['mkfs', '-t', 'xfs', '/dev/sdd'])

    @patch('os.chown')
    @patch('os.stat')
    def test_place_data_on_block_device(self, _stat, _chown):
        self._patch('mount')
        self._patch('copy_files')
        self._patch('umount')
        _stat.return_value.st_uid = 100
        _stat.return_value.st_gid = 100
        ceph_utils.place_data_on_block_device('/dev/sdd', '/var/lib/mysql')
        self.mount.assert_has_calls([
            call('/dev/sdd', '/mnt'),
            call('/dev/sdd', '/var/lib/mysql', persist=True)
        ])
        self.copy_files.assert_called_with('/var/lib/mysql', '/mnt')
        self.umount.assert_called_with('/mnt')
        _chown.assert_called_with('/var/lib/mysql', 100, 100)

    @patch('shutil.copytree')
    @patch('os.listdir')
    @patch('os.path.isdir')
    def test_copy_files_is_dir(self, _isdir, _listdir, _copytree):
        _isdir.return_value = True
        subdirs = ['a', 'b', 'c']
        _listdir.return_value = subdirs
        ceph_utils.copy_files('/source', '/dest')
        for d in subdirs:
            _copytree.assert_has_calls([
                call('/source/{}'.format(d), '/dest/{}'.format(d),
                     False, None)
            ])

    @patch('shutil.copytree')
    @patch('os.listdir')
    @patch('os.path.isdir')
    def test_copy_files_include_symlinks(self, _isdir, _listdir, _copytree):
        _isdir.return_value = True
        subdirs = ['a', 'b', 'c']
        _listdir.return_value = subdirs
        ceph_utils.copy_files('/source', '/dest', True)
        for d in subdirs:
            _copytree.assert_has_calls([
                call('/source/{}'.format(d), '/dest/{}'.format(d),
                     True, None)
            ])

    @patch('shutil.copytree')
    @patch('os.listdir')
    @patch('os.path.isdir')
    def test_copy_files_ignore(self, _isdir, _listdir, _copytree):
        _isdir.return_value = True
        subdirs = ['a', 'b', 'c']
        _listdir.return_value = subdirs
        ceph_utils.copy_files('/source', '/dest', True, False)
        for d in subdirs:
            _copytree.assert_has_calls([
                call('/source/{}'.format(d), '/dest/{}'.format(d),
                     True, False)
            ])

    @patch('shutil.copy2')
    @patch('os.listdir')
    @patch('os.path.isdir')
    def test_copy_files_files(self, _isdir, _listdir, _copy2):
        _isdir.return_value = False
        files = ['a', 'b', 'c']
        _listdir.return_value = files
        ceph_utils.copy_files('/source', '/dest')
        for f in files:
            _copy2.assert_has_calls([
                call('/source/{}'.format(f), '/dest/{}'.format(f))
            ])

    def test_ensure_ceph_storage(self):
        self._patch('pool_exists')
        self.pool_exists.return_value = False
        self._patch('create_pool')
        self._patch('rbd_exists')
        self.rbd_exists.return_value = False
        self._patch('create_rbd_image')
        self._patch('image_mapped')
        self.image_mapped.return_value = False
        self._patch('map_block_storage')
        self._patch('filesystem_mounted')
        self.filesystem_mounted.return_value = False
        self._patch('make_filesystem')
        self._patch('service_stop')
        self._patch('service_start')
        self._patch('service_running')
        self.service_running.return_value = True
        self._patch('place_data_on_block_device')
        _service = 'mysql'
        _pool = 'bar'
        _rbd_img = 'foo'
        _mount = '/var/lib/mysql'
        _services = ['mysql']
        _blk_dev = '/dev/rbd1'
        ceph_utils.ensure_ceph_storage(_service, _pool,
                                       _rbd_img, 1024, _mount,
                                       _blk_dev, 'ext4', _services, 3)
        self.create_pool.assert_called_with(_service, _pool, replicas=3)
        self.create_rbd_image.assert_called_with(_service, _pool,
                                                 _rbd_img, 1024)
        self.map_block_storage.assert_called_with(_service, _pool, _rbd_img)
        self.make_filesystem.assert_called_with(_blk_dev, 'ext4')
        self.service_stop.assert_called_with(_services[0])
        self.place_data_on_block_device.assert_called_with(_blk_dev, _mount)
        self.service_start.assert_called_with(_services[0])

    def test_make_filesystem_default_filesystem(self):
        """make_filesystem() uses ext4 as the default filesystem."""
        device = '/dev/zero'
        ceph_utils.make_filesystem(device)
        self.check_call.assert_called_with(['mkfs', '-t', 'ext4', device])

    def test_make_filesystem_no_device(self):
        """make_filesystem() raises an IOError if the device does not exist."""
        device = '/no/such/device'
        e = self.assertRaises(IOError, ceph_utils.make_filesystem, device,
                              timeout=0)
        self.assertEquals(device, e.filename)
        self.assertEquals(errno.ENOENT, e.errno)
        self.assertEquals(os.strerror(errno.ENOENT), e.strerror)
        self.log.assert_called_with(
            'Gave up waiting on block device %s' % device, level='ERROR')

    @nose.plugins.attrib.attr('slow')
    def test_make_filesystem_timeout(self):
        """
        make_filesystem() allows to specify how long it should wait for the
        device to appear before it fails.
        """
        device = '/no/such/device'
        timeout = 2
        before = time.time()
        self.assertRaises(IOError, ceph_utils.make_filesystem, device,
                          timeout=timeout)
        after = time.time()
        duration = after - before
        self.assertTrue(timeout - duration < 0.1)
        self.log.assert_called_with(
            'Gave up waiting on block device %s' % device, level='ERROR')

    @nose.plugins.attrib.attr('slow')
    def test_device_is_formatted_if_it_appears(self):
        """
        The specified device is formatted if it appears before the timeout
        is reached.
        """

        def create_my_device(filename):
            with open(filename, "w") as device:
                device.write("hello\n")

        temp_dir = mkdtemp()
        self.addCleanup(rmtree, temp_dir)
        device = "%s/mydevice" % temp_dir
        fstype = 'xfs'
        timeout = 4
        t = Timer(2, create_my_device, [device])
        t.start()
        ceph_utils.make_filesystem(device, fstype, timeout)
        self.check_call.assert_called_with(['mkfs', '-t', fstype, device])

    def test_existing_device_is_formatted(self):
        """
        make_filesystem() formats the given device if it exists with the
        specified filesystem.
        """
        device = '/dev/zero'
        fstype = 'xfs'
        ceph_utils.make_filesystem(device, fstype)
        self.check_call.assert_called_with(['mkfs', '-t', fstype, device])
        self.log.assert_called_with(
            'Formatting block device %s as '
            'filesystem %s.' % (device, fstype), level='INFO'
        )

    @patch.object(ceph_utils, 'relation_ids')
    @patch.object(ceph_utils, 'related_units')
    @patch.object(ceph_utils, 'relation_get')
    def test_ensure_ceph_keyring_no_relation_no_data(self, rget, runits, rids):
        rids.return_value = []
        self.assertEquals(False, ceph_utils.ensure_ceph_keyring(service='foo'))
        rids.return_value = ['ceph:0']
        runits.return_value = ['ceph/0']
        rget.return_value = ''
        self.assertEquals(False, ceph_utils.ensure_ceph_keyring(service='foo'))

    @patch.object(ceph_utils, '_keyring_path')
    @patch.object(ceph_utils, 'add_key')
    @patch.object(ceph_utils, 'relation_ids')
    def test_ensure_ceph_keyring_no_relation_but_key(self, rids,
                                                     create, _path):
        rids.return_value = []
        self.assertTrue(ceph_utils.ensure_ceph_keyring(service='foo',
                                                       key='testkey'))
        create.assert_called_with(service='foo', key='testkey')
        _path.assert_called_with('foo')

    @patch.object(ceph_utils, '_keyring_path')
    @patch.object(ceph_utils, 'add_key')
    @patch.object(ceph_utils, 'relation_ids')
    @patch.object(ceph_utils, 'related_units')
    @patch.object(ceph_utils, 'relation_get')
    def test_ensure_ceph_keyring_with_data(self, rget, runits,
                                           rids, create, _path):
        rids.return_value = ['ceph:0']
        runits.return_value = ['ceph/0']
        rget.return_value = 'fookey'
        self.assertEquals(True,
                          ceph_utils.ensure_ceph_keyring(service='foo'))
        create.assert_called_with(service='foo', key='fookey')
        _path.assert_called_with('foo')
        self.assertFalse(self.check_call.called)

        _path.return_value = '/etc/ceph/client.foo.keyring'
        self.assertEquals(
            True,
            ceph_utils.ensure_ceph_keyring(
                service='foo', user='adam', group='users'))
        create.assert_called_with(service='foo', key='fookey')
        _path.assert_called_with('foo')
        self.check_call.assert_called_with([
            'chown',
            'adam.users',
            '/etc/ceph/client.foo.keyring'
        ])

    @patch.object(ceph_utils, 'service_name')
    @patch.object(ceph_utils, 'uuid')
    def test_ceph_broker_rq_class(self, uuid, service_name):
        service_name.return_value = 'service_test'
        uuid.uuid1.return_value = 'uuid'
        rq = ceph_utils.CephBrokerRq()
        rq.add_op_create_pool('pool1', replica_count=1)
        rq.add_op_create_pool('pool1', replica_count=1)
        rq.add_op_create_pool('pool2')
        rq.add_op_create_pool('pool2')
        rq.add_op_create_pool('pool3', group='test')
        rq.add_op_request_access_to_group(name='test')
        rq.add_op_request_access_to_group(name='test')
        rq.add_op_request_access_to_group(name='objects',
                                          key_name='test')
        rq.add_op_request_access_to_group(
            name='others',
            object_prefix_permissions={'rwx': ['prefix1']})
        expected = {
            'api-version': 1,
            'request-id': 'uuid',
            'ops': [{'op': 'create-pool', 'name': 'pool1', 'replicas': 1},
                    {'op': 'create-pool', 'name': 'pool2', 'replicas': 3},
                    {'op': 'create-pool', 'name': 'pool3', 'replicas': 3, 'group': 'test'},
                    {'op': 'add-permissions-to-key', 'group': 'test', 'name': 'service_test'},
                    {'op': 'add-permissions-to-key', 'group': 'objects', 'name': 'test'},
                    {
                        'op': 'add-permissions-to-key',
                        'group': 'others',
                        'name': 'service_test',
                        'object-prefix-permissions': {u'rwx': [u'prefix1']}}]
        }
        request_dict = json.loads(rq.request)
        for key in ['api-version', 'request-id']:
            self.assertEqual(request_dict[key], expected[key])
        for (op_no, expected_op) in enumerate(expected['ops']):
            for key in expected_op.keys():
                self.assertEqual(
                    request_dict['ops'][op_no][key],
                    expected_op[key])

    @patch.object(ceph_utils, 'service_name')
    @patch.object(ceph_utils, 'uuid')
    def test_ceph_broker_rq_class_test_not_equal(self, uuid, service_name):
        service_name.return_value = 'service_test'
        uuid.uuid1.return_value = 'uuid'
        rq1 = ceph_utils.CephBrokerRq()
        rq1.add_op_create_pool('pool1')
        rq1.add_op_request_access_to_group(name='test')
        rq1.add_op_request_access_to_group(name='objects',
                                           permission='rwx')
        rq2 = ceph_utils.CephBrokerRq()
        rq2.add_op_create_pool('pool1')
        rq2.add_op_request_access_to_group(name='test')
        rq2.add_op_request_access_to_group(name='objects',
                                           permission='r')
        self.assertFalse(rq1 == rq2)
        # now check equality check for common properties
        rq1 = ceph_utils.CephBrokerRq()
        rq1.add_op_create_replicated_pool('pool1')
        rq2 = ceph_utils.CephBrokerRq()
        rq2.add_op_create_replicated_pool('pool1')
        self.assertTrue(rq1 == rq2)
        rq1 = ceph_utils.CephBrokerRq()
        rq1.add_op_create_replicated_pool('pool1', compression_mode='none')
        rq2 = ceph_utils.CephBrokerRq()
        rq2.add_op_create_replicated_pool('pool1', compression_mode='passive')
        self.assertFalse(rq1 == rq2)

    def test_ceph_broker_rsp_class(self):
        rsp = ceph_utils.CephBrokerRsp(json.dumps({'exit-code': 0,
                                                   'stderr': "Success"}))
        self.assertEqual(rsp.exit_code, 0)
        self.assertEqual(rsp.exit_msg, "Success")
        self.assertEqual(rsp.request_id, None)

    def test_ceph_broker_rsp_class_rqid(self):
        rsp = ceph_utils.CephBrokerRsp(json.dumps({'exit-code': 0,
                                                   'stderr': "Success",
                                                   'request-id': 'reqid1'}))
        self.assertEqual(rsp.exit_code, 0)
        self.assertEqual(rsp.exit_msg, 'Success')
        self.assertEqual(rsp.request_id, 'reqid1')

    def setup_client_relation(self, relation):
        relation = FakeRelation(relation)
        self.relation_get.side_effect = relation.get
        self.relation_ids.side_effect = relation.relation_ids
        self.related_units.side_effect = relation.related_units

    #    @patch.object(ceph_utils, 'uuid')
    #    @patch.object(ceph_utils, 'local_unit')
    #    def test_get_request_states(self, mlocal_unit, muuid):
    #        muuid.uuid1.return_value = '0bc7dc54'
    @patch.object(ceph_utils, 'local_unit')
    def test_get_request_states(self, mlocal_unit):
        mlocal_unit.return_value = 'glance/0'
        self.setup_client_relation(CEPH_CLIENT_RELATION)
        rq = ceph_utils.CephBrokerRq()
        rq.add_op_create_pool(name='glance', replica_count=3)
        expect = {'ceph:8': {'complete': True, 'sent': True}}
        self.assertEqual(ceph_utils.get_request_states(rq), expect)

    @patch.object(ceph_utils, 'local_unit')
    def test_get_request_states_newrq(self, mlocal_unit):
        mlocal_unit.return_value = 'glance/0'
        self.setup_client_relation(CEPH_CLIENT_RELATION)
        rq = ceph_utils.CephBrokerRq()
        rq.add_op_create_pool(name='glance', replica_count=4)
        expect = {'ceph:8': {'complete': False, 'sent': False}}
        self.assertEqual(ceph_utils.get_request_states(rq), expect)

    @patch.object(ceph_utils, 'local_unit')
    def test_get_request_states_pendingrq(self, mlocal_unit):
        mlocal_unit.return_value = 'glance/0'
        rel = copy.deepcopy(CEPH_CLIENT_RELATION)
        del rel['ceph:8']['ceph/0']['broker-rsp-glance-0']
        self.setup_client_relation(rel)
        rq = ceph_utils.CephBrokerRq()
        rq.add_op_create_pool(name='glance', replica_count=3)
        expect = {'ceph:8': {'complete': False, 'sent': True}}
        self.assertEqual(ceph_utils.get_request_states(rq), expect)

    @patch.object(ceph_utils, 'local_unit')
    def test_get_request_states_failedrq(self, mlocal_unit):
        mlocal_unit.return_value = 'glance/0'
        rel = copy.deepcopy(CEPH_CLIENT_RELATION)
        rel['ceph:8']['ceph/0']['broker-rsp-glance-0'] = '{"request-id": "0bc7dc54", "exit-code": 1}'
        self.setup_client_relation(rel)
        rq = ceph_utils.CephBrokerRq()
        rq.add_op_create_pool(name='glance', replica_count=3)
        expect = {'ceph:8': {'complete': False, 'sent': True}}
        self.assertEqual(ceph_utils.get_request_states(rq), expect)

    @patch.object(ceph_utils, 'local_unit')
    def test_is_request_sent(self, mlocal_unit):
        mlocal_unit.return_value = 'glance/0'
        self.setup_client_relation(CEPH_CLIENT_RELATION)
        rq = ceph_utils.CephBrokerRq()
        rq.add_op_create_pool(name='glance', replica_count=3)
        self.assertTrue(ceph_utils.is_request_sent(rq))

    @patch.object(ceph_utils, 'local_unit')
    def test_is_request_sent_newrq(self, mlocal_unit):
        mlocal_unit.return_value = 'glance/0'
        self.setup_client_relation(CEPH_CLIENT_RELATION)
        rq = ceph_utils.CephBrokerRq()
        rq.add_op_create_pool(name='glance', replica_count=4)
        self.assertFalse(ceph_utils.is_request_sent(rq))

    @patch.object(ceph_utils, 'local_unit')
    def test_is_request_sent_pending(self, mlocal_unit):
        mlocal_unit.return_value = 'glance/0'
        rel = copy.deepcopy(CEPH_CLIENT_RELATION)
        del rel['ceph:8']['ceph/0']['broker-rsp-glance-0']
        self.setup_client_relation(rel)
        rq = ceph_utils.CephBrokerRq()
        rq.add_op_create_pool(name='glance', replica_count=3)
        self.assertTrue(ceph_utils.is_request_sent(rq))

    @patch.object(ceph_utils, 'local_unit')
    def test_is_request_sent_legacy(self, mlocal_unit):
        mlocal_unit.return_value = 'glance/0'
        self.setup_client_relation(CEPH_CLIENT_RELATION_LEGACY)
        rq = ceph_utils.CephBrokerRq()
        rq.add_op_create_pool(name='glance', replica_count=3)
        self.assertTrue(ceph_utils.is_request_sent(rq))

    @patch.object(ceph_utils, 'local_unit')
    def test_is_request_sent_legacy_newrq(self, mlocal_unit):
        mlocal_unit.return_value = 'glance/0'
        self.setup_client_relation(CEPH_CLIENT_RELATION_LEGACY)
        rq = ceph_utils.CephBrokerRq()
        rq.add_op_create_pool(name='glance', replica_count=4)
        self.assertFalse(ceph_utils.is_request_sent(rq))

    @patch.object(ceph_utils, 'local_unit')
    def test_is_request_sent_legacy_pending(self, mlocal_unit):
        mlocal_unit.return_value = 'glance/0'
        rel = copy.deepcopy(CEPH_CLIENT_RELATION_LEGACY)
        del rel['ceph:8']['ceph/0']['broker_rsp']
        rq = ceph_utils.CephBrokerRq()
        rq.add_op_create_pool(name='glance', replica_count=3)
        self.assertTrue(ceph_utils.is_request_sent(rq))

    @patch.object(ceph_utils, 'uuid')
    @patch.object(ceph_utils, 'local_unit')
    def test_is_request_complete(self, mlocal_unit, muuid):
        muuid.uuid1.return_value = '0bc7dc54'
        mlocal_unit.return_value = 'glance/0'
        self.setup_client_relation(CEPH_CLIENT_RELATION)
        rq = ceph_utils.CephBrokerRq()
        rq.add_op_create_pool(name='glance', replica_count=3)
        self.assertTrue(ceph_utils.is_request_complete(rq))

    @patch.object(ceph_utils, 'local_unit')
    def test_is_request_complete_newrq(self, mlocal_unit):
        mlocal_unit.return_value = 'glance/0'
        self.setup_client_relation(CEPH_CLIENT_RELATION)
        rq = ceph_utils.CephBrokerRq()
        rq.add_op_create_pool(name='glance', replica_count=4)
        self.assertFalse(ceph_utils.is_request_complete(rq))

    @patch.object(ceph_utils, 'local_unit')
    def test_is_request_complete_pending(self, mlocal_unit):
        mlocal_unit.return_value = 'glance/0'
        rel = copy.deepcopy(CEPH_CLIENT_RELATION)
        del rel['ceph:8']['ceph/0']['broker-rsp-glance-0']
        self.setup_client_relation(rel)
        rq = ceph_utils.CephBrokerRq()
        rq.add_op_create_pool(name='glance', replica_count=3)
        self.assertFalse(ceph_utils.is_request_complete(rq))

    @patch.object(ceph_utils, 'local_unit')
    def test_is_request_complete_legacy(self, mlocal_unit):
        mlocal_unit.return_value = 'glance/0'
        self.setup_client_relation(CEPH_CLIENT_RELATION_LEGACY)
        rq = ceph_utils.CephBrokerRq()
        rq.add_op_create_pool(name='glance', replica_count=3)
        self.assertTrue(ceph_utils.is_request_complete(rq))

    @patch.object(ceph_utils, 'local_unit')
    def test_is_request_complete_legacy_newrq(self, mlocal_unit):
        mlocal_unit.return_value = 'glance/0'
        self.setup_client_relation(CEPH_CLIENT_RELATION_LEGACY)
        rq = ceph_utils.CephBrokerRq()
        rq.add_op_create_pool(name='glance', replica_count=4)
        self.assertFalse(ceph_utils.is_request_complete(rq))

    @patch.object(ceph_utils, 'local_unit')
    def test_is_request_complete_legacy_pending(self, mlocal_unit):
        mlocal_unit.return_value = 'glance/0'
        rel = copy.deepcopy(CEPH_CLIENT_RELATION_LEGACY)
        del rel['ceph:8']['ceph/0']['broker_rsp']
        self.setup_client_relation(rel)
        rq = ceph_utils.CephBrokerRq()
        rq.add_op_create_pool(name='glance', replica_count=3)
        self.assertFalse(ceph_utils.is_request_complete(rq))

    def test_equivalent_broker_requests(self):
        rq1 = ceph_utils.CephBrokerRq()
        rq1.add_op_create_pool(name='glance', replica_count=4)
        rq2 = ceph_utils.CephBrokerRq()
        rq2.add_op_create_pool(name='glance', replica_count=4)
        self.assertTrue(rq1 == rq2)

    def test_equivalent_broker_requests_diff1(self):
        rq1 = ceph_utils.CephBrokerRq()
        rq1.add_op_create_pool(name='glance', replica_count=3)
        rq2 = ceph_utils.CephBrokerRq()
        rq2.add_op_create_pool(name='glance', replica_count=4)
        self.assertFalse(rq1 == rq2)

    def test_equivalent_broker_requests_diff2(self):
        rq1 = ceph_utils.CephBrokerRq()
        rq1.add_op_create_pool(name='glance', replica_count=3)
        rq2 = ceph_utils.CephBrokerRq()
        rq2.add_op_create_pool(name='cinder', replica_count=3)
        self.assertFalse(rq1 == rq2)

    def test_equivalent_broker_requests_diff3(self):
        rq1 = ceph_utils.CephBrokerRq()
        rq1.add_op_create_pool(name='glance', replica_count=3)
        rq2 = ceph_utils.CephBrokerRq(api_version=2)
        rq2.add_op_create_pool(name='glance', replica_count=3)
        self.assertFalse(rq1 == rq2)

    @patch.object(ceph_utils, 'uuid')
    @patch.object(ceph_utils, 'local_unit')
    def test_is_request_complete_for_rid(self, mlocal_unit, muuid):
        muuid.uuid1.return_value = '0bc7dc54'
        req = ceph_utils.CephBrokerRq()
        req.add_op_create_pool(name='glance', replica_count=3)
        mlocal_unit.return_value = 'glance/0'
        self.setup_client_relation(CEPH_CLIENT_RELATION)
        self.assertTrue(ceph_utils.is_request_complete_for_rid(req, 'ceph:8'))

    @patch.object(ceph_utils, 'uuid')
    @patch.object(ceph_utils, 'local_unit')
    def test_is_request_complete_for_rid_newrq(self, mlocal_unit, muuid):
        muuid.uuid1.return_value = 'a44c0fa6'
        req = ceph_utils.CephBrokerRq()
        req.add_op_create_pool(name='glance', replica_count=4)
        mlocal_unit.return_value = 'glance/0'
        self.setup_client_relation(CEPH_CLIENT_RELATION)
        self.assertFalse(ceph_utils.is_request_complete_for_rid(req, 'ceph:8'))

    @patch.object(ceph_utils, 'uuid')
    @patch.object(ceph_utils, 'local_unit')
    def test_is_request_complete_for_rid_failed(self, mlocal_unit, muuid):
        muuid.uuid1.return_value = '0bc7dc54'
        req = ceph_utils.CephBrokerRq()
        req.add_op_create_pool(name='glance', replica_count=4)
        mlocal_unit.return_value = 'glance/0'
        rel = copy.deepcopy(CEPH_CLIENT_RELATION)
        rel['ceph:8']['ceph/0']['broker-rsp-glance-0'] = '{"request-id": "0bc7dc54", "exit-code": 1}'
        self.setup_client_relation(rel)
        self.assertFalse(ceph_utils.is_request_complete_for_rid(req, 'ceph:8'))

    @patch.object(ceph_utils, 'uuid')
    @patch.object(ceph_utils, 'local_unit')
    def test_is_request_complete_for_rid_pending(self, mlocal_unit, muuid):
        muuid.uuid1.return_value = '0bc7dc54'
        req = ceph_utils.CephBrokerRq()
        req.add_op_create_pool(name='glance', replica_count=4)
        mlocal_unit.return_value = 'glance/0'
        rel = copy.deepcopy(CEPH_CLIENT_RELATION)
        del rel['ceph:8']['ceph/0']['broker-rsp-glance-0']
        self.setup_client_relation(rel)
        self.assertFalse(ceph_utils.is_request_complete_for_rid(req, 'ceph:8'))

    @patch.object(ceph_utils, 'uuid')
    @patch.object(ceph_utils, 'local_unit')
    def test_is_request_complete_for_rid_legacy(self, mlocal_unit, muuid):
        muuid.uuid1.return_value = '0bc7dc54'
        req = ceph_utils.CephBrokerRq()
        req.add_op_create_pool(name='glance', replica_count=3)
        mlocal_unit.return_value = 'glance/0'
        self.setup_client_relation(CEPH_CLIENT_RELATION_LEGACY)
        self.assertTrue(ceph_utils.is_request_complete_for_rid(req, 'ceph:8'))

    @patch.object(ceph_utils, 'local_unit')
    def test_get_broker_rsp_key(self, mlocal_unit):
        mlocal_unit.return_value = 'glance/0'
        self.assertEqual(ceph_utils.get_broker_rsp_key(), 'broker-rsp-glance-0')

    @patch.object(ceph_utils, 'local_unit')
    def test_send_request_if_needed(self, mlocal_unit):
        mlocal_unit.return_value = 'glance/0'
        self.setup_client_relation(CEPH_CLIENT_RELATION)
        rq = ceph_utils.CephBrokerRq()
        rq.add_op_create_pool(name='glance', replica_count=3)
        ceph_utils.send_request_if_needed(rq)
        self.relation_set.assert_has_calls([])

    @patch.object(ceph_utils, 'uuid')
    @patch.object(ceph_utils, 'local_unit')
    def test_send_request_if_needed_newrq(self, mlocal_unit, muuid):
        muuid.uuid1.return_value = 'de67511e'
        mlocal_unit.return_value = 'glance/0'
        self.setup_client_relation(CEPH_CLIENT_RELATION)
        rq = ceph_utils.CephBrokerRq()
        rq.add_op_create_pool(name='glance', replica_count=4)
        ceph_utils.send_request_if_needed(rq)
        actual = json.loads(self.relation_set.call_args_list[0][1]['broker_req'])
        self.assertEqual(actual['api-version'], 1)
        self.assertEqual(actual['request-id'], 'de67511e')
        self.assertEqual(actual['ops'][0]['replicas'], 4)
        self.assertEqual(actual['ops'][0]['op'], 'create-pool')
        self.assertEqual(actual['ops'][0]['name'], 'glance')

    @patch.object(ceph_utils, 'config')
    def test_ceph_conf_context(self, mock_config):
        mock_config.return_value = "{'osd': {'foo': 1}}"
        ctxt = ceph_utils.CephConfContext()()
        self.assertEqual({'osd': {'foo': 1}}, ctxt)
        ctxt = ceph_utils.CephConfContext(['osd', 'mon'])()
        mock_config.return_value = ("{'osd': {'foo': 1},"
                                    "'unknown': {'blah': 1}}")
        self.assertEqual({'osd': {'foo': 1}}, ctxt)

    @patch.object(ceph_utils, 'get_osd_settings')
    @patch.object(ceph_utils, 'config')
    def test_ceph_osd_conf_context_conflict(self, mock_config,
                                            mock_get_osd_settings):
        mock_config.return_value = "{'osd': {'osd heartbeat grace': 20}}"
        mock_get_osd_settings.return_value = {
            'osd heartbeat grace': 25,
            'osd heartbeat interval': 5}
        ctxt = ceph_utils.CephOSDConfContext()()
        self.assertEqual(ctxt, {
            'osd': collections.OrderedDict([('osd heartbeat grace', 20)]),
            'osd_from_client': collections.OrderedDict(
                [('osd heartbeat interval', 5)]),
            'osd_from_client_conflict': collections.OrderedDict(
                [('osd heartbeat grace', 25)])})

    @patch.object(ceph_utils, 'local_unit', lambda: "nova-compute/0")
    def test_is_broker_action_done(self):
        tmpdir = mkdtemp()
        try:
            db_path = '{}/kv.db'.format(tmpdir)
            with patch('charmhelpers.core.unitdata._KV', Storage(db_path)):
                rq_id = "3d03e9f6-4c36-11e7-89ba-fa163e7c7ec6"
                broker_key = ceph_utils.get_broker_rsp_key()
                self.relation_get.return_value = {broker_key:
                                                  json.dumps({"request-id":
                                                              rq_id,
                                                              "exit-code": 0})}
                action = 'restart_nova_compute'
                ret = ceph_utils.is_broker_action_done(action, rid="ceph:1",
                                                       unit="ceph/0")
                self.relation_get.assert_has_calls([call(rid='ceph:1', unit='ceph/0')])
                self.assertFalse(ret)

                ceph_utils.mark_broker_action_done(action)
                self.assertTrue(os.path.exists(tmpdir))
                ret = ceph_utils.is_broker_action_done(action, rid="ceph:1",
                                                       unit="ceph/0")
                self.assertTrue(ret)
        finally:
            if os.path.exists(tmpdir):
                shutil.rmtree(tmpdir)

    def test_has_broker_rsp(self):
        rq_id = "3d03e9f6-4c36-11e7-89ba-fa163e7c7ec6"
        broker_key = ceph_utils.get_broker_rsp_key()
        self.relation_get.return_value = {broker_key:
                                          json.dumps({"request-id":
                                                      rq_id,
                                                      "exit-code": 0})}
        ret = ceph_utils.has_broker_rsp(rid="ceph:1", unit="ceph/0")
        self.assertTrue(ret)
        self.relation_get.assert_has_calls([call(rid='ceph:1', unit='ceph/0')])

        self.relation_get.return_value = {'something_else':
                                          json.dumps({"request-id":
                                                      rq_id,
                                                      "exit-code": 0})}
        ret = ceph_utils.has_broker_rsp(rid="ceph:1", unit="ceph/0")
        self.assertFalse(ret)

        self.relation_get.return_value = None
        ret = ceph_utils.has_broker_rsp(rid="ceph:1", unit="ceph/0")
        self.assertFalse(ret)

    @patch.object(ceph_utils, 'local_unit', lambda: "nova-compute/0")
    def test_mark_broker_action_done(self):
        tmpdir = mkdtemp()
        try:
            db_path = '{}/kv.db'.format(tmpdir)
            with patch('charmhelpers.core.unitdata._KV', Storage(db_path)):
                rq_id = "3d03e9f6-4c36-11e7-89ba-fa163e7c7ec6"
                broker_key = ceph_utils.get_broker_rsp_key()
                self.relation_get.return_value = {broker_key:
                                                  json.dumps({"request-id":
                                                              rq_id})}
                action = 'restart_nova_compute'
                ceph_utils.mark_broker_action_done(action, rid="ceph:1",
                                                   unit="ceph/0")
                key = 'unit_0_ceph_broker_action.{}'.format(action)
                self.relation_get.assert_has_calls([call(rid='ceph:1', unit='ceph/0')])
                kvstore = Storage(db_path)
                self.assertEqual(kvstore.get(key=key), rq_id)
        finally:
            if os.path.exists(tmpdir):
                shutil.rmtree(tmpdir)

    def test__partial_build_common_op_create(self):
        self.maxDiff = None
        rq = ceph_utils.CephBrokerRq()
        expect = {
            'app-name': None,
            'compression-algorithm': 'lz4',
            'compression-mode': 'passive',
            'compression-required-ratio': 0.85,
            'compression-min-blob-size': 131072,
            'compression-min-blob-size-hdd': 131072,
            'compression-min-blob-size-ssd': 8192,
            'compression-max-blob-size': 524288,
            'compression-max-blob-size-hdd': 524288,
            'compression-max-blob-size-ssd': 65536,
            'group': None,
            'max-bytes': None,
            'max-objects': None,
            'group-namespace': None,
            'rbd-mirroring-mode': 'pool',
            'weight': None,
        }
        self.assertDictEqual(
            rq._partial_build_common_op_create(
                compression_algorithm='lz4',
                compression_mode='passive',
                compression_required_ratio=0.85,
                compression_min_blob_size=131072,
                compression_min_blob_size_hdd=131072,
                compression_min_blob_size_ssd=8192,
                compression_max_blob_size=524288,
                compression_max_blob_size_hdd=524288,
                compression_max_blob_size_ssd=65536),
            expect)

    def test_add_op_create_replicated_pool(self):
        base_op = {'app-name': None,
                   'compression-algorithm': None,
                   'compression-max-blob-size': None,
                   'compression-max-blob-size-hdd': None,
                   'compression-max-blob-size-ssd': None,
                   'compression-min-blob-size': None,
                   'compression-min-blob-size-hdd': None,
                   'compression-min-blob-size-ssd': None,
                   'compression-mode': None,
                   'compression-required-ratio': None,
                   'group': None,
                   'group-namespace': None,
                   'max-bytes': None,
                   'max-objects': None,
                   'name': 'apool',
                   'op': 'create-pool',
                   'pg_num': None,
                   'rbd-mirroring-mode': 'pool',
                   'replicas': 3,
                   'weight': None}
        rq = ceph_utils.CephBrokerRq()
        rq.add_op_create_replicated_pool('apool')
        self.assertDictEqual(rq.ops[0], base_op)
        self.assertRaises(
            ValueError, rq.add_op_create_pool, 'apool', pg_num=51, weight=100)
        rq = ceph_utils.CephBrokerRq()
        self.assertRaises(
            ValueError,
            rq.add_op_create_replicated_pool, 'apool',
            compression_algorithm='invalid')
        rq = ceph_utils.CephBrokerRq()
        self.assertRaises(
            ValueError,
            rq.add_op_create_replicated_pool, 'apool',
            compression_mode='invalid')
        # these parameters should be float / int
        rq = ceph_utils.CephBrokerRq()
        self.assertRaises(
            ValueError,
            rq.add_op_create_replicated_pool, 'apool',
            compression_required_ratio='1')
        rq = ceph_utils.CephBrokerRq()
        self.assertRaises(
            ValueError,
            rq.add_op_create_replicated_pool, 'apool',
            compression_min_blob_size='1')
        rq = ceph_utils.CephBrokerRq()
        self.assertRaises(
            ValueError,
            rq.add_op_create_replicated_pool, 'apool',
            compression_min_blob_size_hdd='1')
        rq = ceph_utils.CephBrokerRq()
        self.assertRaises(
            ValueError,
            rq.add_op_create_replicated_pool, 'apool',
            compression_min_blob_size_ssd='1')
        rq = ceph_utils.CephBrokerRq()
        self.assertRaises(
            ValueError,
            rq.add_op_create_replicated_pool, 'apool',
            compression_max_blob_size='1')
        rq = ceph_utils.CephBrokerRq()
        self.assertRaises(
            ValueError,
            rq.add_op_create_replicated_pool, 'apool',
            compression_max_blob_size_hdd='1')
        rq = ceph_utils.CephBrokerRq()
        self.assertRaises(
            ValueError,
            rq.add_op_create_replicated_pool, 'apool',
            compression_max_blob_size_ssd='1')
        rq = ceph_utils.CephBrokerRq()
        rq.add_op_create_pool('apool', replica_count=42)
        op = base_op.copy()
        op['replicas'] = 42
        self.assertEqual(rq.ops, [op])
        rq = ceph_utils.CephBrokerRq()
        rq.add_op_create_replicated_pool('apool', pg_num=42)
        op = base_op.copy()
        op['pg_num'] = 42
        self.assertEqual(rq.ops, [op])
        rq = ceph_utils.CephBrokerRq()
        rq.add_op_create_replicated_pool('apool', weight=42)
        op = base_op.copy()
        op['weight'] = 42
        self.assertEqual(rq.ops, [op])
        rq = ceph_utils.CephBrokerRq()
        rq.add_op_create_replicated_pool('apool', group=51)
        op = base_op.copy()
        op['group'] = 51
        self.assertEqual(rq.ops, [op])
        rq = ceph_utils.CephBrokerRq()
        rq.add_op_create_replicated_pool('apool', namespace='sol-iii')
        op = base_op.copy()
        op['group-namespace'] = 'sol-iii'
        self.assertEqual(rq.ops, [op])
        rq = ceph_utils.CephBrokerRq()
        rq.add_op_create_replicated_pool('apool', app_name='earth')
        op = base_op.copy()
        op['app-name'] = 'earth'
        self.assertEqual(rq.ops, [op])
        rq = ceph_utils.CephBrokerRq()
        rq.add_op_create_replicated_pool('apool', max_bytes=42)
        op = base_op.copy()
        op['max-bytes'] = 42
        self.assertEqual(rq.ops, [op])
        rq = ceph_utils.CephBrokerRq()
        rq.add_op_create_replicated_pool('apool', max_objects=42)
        op = base_op.copy()
        op['max-objects'] = 42
        self.assertEqual(rq.ops, [op])
        rq = ceph_utils.CephBrokerRq()
        rq.add_op_create_replicated_pool('apool', rbd_mirroring_mode='pool')
        op = base_op.copy()
        op['rbd-mirroring-mode'] = 'pool'
        self.assertEqual(rq.ops, [op])
        rq = ceph_utils.CephBrokerRq()
        rq.add_op_create_replicated_pool('apool', rbd_mirroring_mode='image')
        op = base_op.copy()
        op['rbd-mirroring-mode'] = 'image'
        self.assertEqual(rq.ops, [op])

    def test_add_op_create_erasure_pool(self):
        base_op = {'app-name': None,
                   'allow-ec-overwrites': False,
                   'compression-algorithm': None,
                   'compression-max-blob-size': None,
                   'compression-max-blob-size-hdd': None,
                   'compression-max-blob-size-ssd': None,
                   'compression-min-blob-size': None,
                   'compression-min-blob-size-hdd': None,
                   'compression-min-blob-size-ssd': None,
                   'compression-mode': None,
                   'compression-required-ratio': None,
                   'erasure-profile': None,
                   'group': None,
                   'group-namespace': None,
                   'max-bytes': None,
                   'max-objects': None,
                   'name': 'apool',
                   'op': 'create-pool',
                   'pool-type': 'erasure',
                   'rbd-mirroring-mode': 'pool',
                   'weight': None}
        rq = ceph_utils.CephBrokerRq()
        rq.add_op_create_erasure_pool('apool')
        self.assertDictEqual(rq.ops[0], base_op)
        rq = ceph_utils.CephBrokerRq()
        rq.add_op_create_erasure_pool('apool', weight=42)
        op = base_op.copy()
        op['weight'] = 42
        self.assertEqual(rq.ops, [op])
        rq = ceph_utils.CephBrokerRq()
        rq.add_op_create_erasure_pool('apool', group=51)
        op = base_op.copy()
        op['group'] = 51
        self.assertEqual(rq.ops, [op])
        rq = ceph_utils.CephBrokerRq()
        rq.add_op_create_erasure_pool('apool', app_name='earth')
        op = base_op.copy()
        op['app-name'] = 'earth'
        self.assertEqual(rq.ops, [op])
        rq = ceph_utils.CephBrokerRq()
        rq.add_op_create_erasure_pool('apool', max_bytes=42)
        op = base_op.copy()
        op['max-bytes'] = 42
        self.assertEqual(rq.ops, [op])
        rq = ceph_utils.CephBrokerRq()
        rq.add_op_create_erasure_pool('apool', max_objects=42)
        op = base_op.copy()
        op['max-objects'] = 42
        self.assertEqual(rq.ops, [op])

    @patch.object(ceph_utils, 'local_unit')
    def test_get_previous_request(self, _local_unit):
        raw_request = CEPH_CLIENT_RELATION['ceph:8']['glance/0']['broker_req']
        self.relation_get.return_value = raw_request
        req = ceph_utils.get_previous_request('aRid')
        self.assertDictEqual(json.loads(req.request), json.loads(raw_request))
        self.relation_get.assert_called_once_with(
            attribute='broker_req', rid='aRid', unit=_local_unit())

    @patch.object(ceph_utils, 'uuid')
    def test_CephBrokerRq__init__(self, _uuid):
        raw_request = CEPH_CLIENT_RELATION['ceph:8']['glance/0']['broker_req']
        request = json.loads(raw_request)
        req1 = ceph_utils.CephBrokerRq(api_version=request['api-version'],
                                       request_id=request['request-id'])
        req1.set_ops(request['ops'])
        req2 = ceph_utils.CephBrokerRq(raw_request_data=raw_request)
        self.assertDictEqual(
            json.loads(req1.request),
            json.loads(req2.request))
        _uuid.uuid1.return_value = 'fake-uuid'
        new_req = ceph_utils.CephBrokerRq()
        expect = {
            'api-version': 1,
            'request-id': 'fake-uuid',
            'ops': [],
        }
        self.assertDictEqual(
            json.loads(new_req.request), expect)

    def test_update_pool(self):
        ceph_utils.update_pool('aUser', 'aPool', {'aKey': 'aValue'})
        self.check_call.assert_called_once_with([
            'ceph', '--id', 'aUser', 'osd', 'pool', 'set',
            'aPool', 'aKey', 'aValue'])
        self.check_call.reset_mock()
        ceph_utils.update_pool('aUser', 'aPool', {
            'aKey': 'aValue',
            'anotherKey': 'anotherValue'})
        self.check_call.assert_has_calls([
            call(['ceph', '--id', 'aUser', 'osd', 'pool', 'set',
                  'aPool', 'aKey', 'aValue']),
            call(['ceph', '--id', 'aUser', 'osd', 'pool', 'set',
                  'aPool', 'anotherKey', 'anotherValue']),
        ], any_order=True)
