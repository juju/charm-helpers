from mock import patch, MagicMock, call

from subprocess import CalledProcessError
from testtools import TestCase

import charmhelpers.contrib.hahelpers.cluster as cluster_utils

CRM_STATUS = b'''
Last updated: Thu May 14 14:46:35 2015
Last change: Thu May 14 14:43:51 2015 via crmd on juju-trusty-machine-1
Stack: corosync
Current DC: juju-trusty-machine-2 (168108171) - partition with quorum
Version: 1.1.10-42f2063
3 Nodes configured
4 Resources configured


Online: [ juju-trusty-machine-1 juju-trusty-machine-2 juju-trusty-machine-3 ]

 Resource Group: grp_percona_cluster
      res_mysql_vip      (ocf::heartbeat:IPaddr2):       Started juju-trusty-machine-1
       Clone Set: cl_mysql_monitor [res_mysql_monitor]
            Started: [ juju-trusty-machine-1 juju-trusty-machine-2 juju-trusty-machine-3 ]
'''

CRM_DC_NONE = b'''
Last updated: Thu May 14 14:46:35 2015
Last change: Thu May 14 14:43:51 2015 via crmd on juju-trusty-machine-1
Stack: corosync
Current DC: NONE
1 Nodes configured, 2 expected votes
0 Resources configured


Node node1: UNCLEAN (offline)
'''


class ClusterUtilsTests(TestCase):
    def setUp(self):
        super(ClusterUtilsTests, self).setUp()
        [self._patch(m) for m in [
            'log',
            'relation_ids',
            'relation_list',
            'relation_get',
            'get_unit_hostname',
            'config_get',
            'unit_get',
        ]]

    def _patch(self, method):
        _m = patch.object(cluster_utils, method)
        mock = _m.start()
        self.addCleanup(_m.stop)
        setattr(self, method, mock)

    def test_is_clustered(self):
        '''It determines whether or not a unit is clustered'''
        self.relation_ids.return_value = ['ha:0']
        self.relation_list.return_value = ['ha/0']
        self.relation_get.return_value = 'yes'
        self.assertTrue(cluster_utils.is_clustered())

    def test_is_not_clustered(self):
        '''It determines whether or not a unit is clustered'''
        self.relation_ids.return_value = ['ha:0']
        self.relation_list.return_value = ['ha/0']
        self.relation_get.return_value = None
        self.assertFalse(cluster_utils.is_clustered())

    @patch('subprocess.check_output')
    def test_is_crm_dc(self, check_output):
        '''It determines its unit is leader'''
        self.get_unit_hostname.return_value = 'juju-trusty-machine-2'
        check_output.return_value = CRM_STATUS
        self.assertTrue(cluster_utils.is_crm_dc())

    @patch('subprocess.check_output')
    def test_is_crm_dc_no_cluster(self, check_output):
        '''It is not leader if there is no cluster up'''
        def r(*args, **kwargs):
            raise CalledProcessError(1, 'crm')

        check_output.side_effect = r
        self.assertRaises(cluster_utils.CRMDCNotFound, cluster_utils.is_crm_dc)

    @patch('subprocess.check_output')
    def test_is_crm_dc_false(self, check_output):
        '''It determines its unit is leader'''
        self.get_unit_hostname.return_value = 'juju-trusty-machine-1'
        check_output.return_value = CRM_STATUS
        self.assertFalse(cluster_utils.is_crm_dc())

    @patch('subprocess.check_output')
    def test_is_crm_dc_current_none(self, check_output):
        '''It determines its unit is leader'''
        self.get_unit_hostname.return_value = 'juju-trusty-machine-1'
        check_output.return_value = CRM_DC_NONE
        self.assertRaises(cluster_utils.CRMDCNotFound, cluster_utils.is_crm_dc)

    @patch('subprocess.check_output')
    def test_is_crm_leader(self, check_output):
        '''It determines its unit is leader'''
        self.get_unit_hostname.return_value = 'node1'
        crm = b'resource vip is running on: node1'
        check_output.return_value = crm
        self.assertTrue(cluster_utils.is_crm_leader('vip'))

    @patch('charmhelpers.core.decorators.time')
    @patch('subprocess.check_output')
    def test_is_not_leader(self, check_output, mock_time):
        '''It determines its unit is not leader'''
        self.get_unit_hostname.return_value = 'node1'
        crm = b'resource vip is running on: node2'
        check_output.return_value = crm
        self.assertFalse(cluster_utils.is_crm_leader('some_resource'))
        self.assertFalse(mock_time.called)

    @patch('charmhelpers.core.decorators.log')
    @patch('charmhelpers.core.decorators.time')
    @patch('subprocess.check_output')
    def test_is_not_leader_resource_not_exists(self, check_output, mock_time,
                                               mock_log):
        '''It determines its unit is not leader'''
        self.get_unit_hostname.return_value = 'node1'
        check_output.return_value = "resource vip is NOT running"
        self.assertRaises(cluster_utils.CRMResourceNotFound,
                          cluster_utils.is_crm_leader, 'vip')
        mock_time.assert_has_calls([call.sleep(2), call.sleep(4),
                                    call.sleep(6)])

    @patch('charmhelpers.core.decorators.time')
    @patch('subprocess.check_output')
    def test_is_crm_leader_no_cluster(self, check_output, mock_time):
        '''It is not leader if there is no cluster up'''
        check_output.side_effect = CalledProcessError(1, 'crm')
        self.assertFalse(cluster_utils.is_crm_leader('vip'))
        self.assertFalse(mock_time.called)

    @patch.object(cluster_utils, 'is_crm_dc')
    def test_is_crm_leader_dc_resource(self, _is_crm_dc):
        '''Call out to is_crm_dc'''
        cluster_utils.is_crm_leader(cluster_utils.DC_RESOURCE_NAME)
        _is_crm_dc.assert_called_with()

    def test_peer_units(self):
        '''It lists all peer units for cluster relation'''
        peers = ['peer_node/1', 'peer_node/2']
        self.relation_ids.return_value = ['cluster:0']
        self.relation_list.return_value = peers
        self.assertEquals(peers, cluster_utils.peer_units())

    def test_peer_ips(self):
        '''Get a dict of peers and their ips'''
        peers = {
            'peer_node/1': '10.0.0.1',
            'peer_node/2': '10.0.0.2',
        }

        def _relation_get(attr, rid, unit):
            return peers[unit]
        self.relation_ids.return_value = ['cluster:0']
        self.relation_list.return_value = peers.keys()
        self.relation_get.side_effect = _relation_get
        self.assertEquals(peers, cluster_utils.peer_ips())

    @patch('os.getenv')
    def test_is_oldest_peer(self, getenv):
        '''It detects local unit is the oldest of all peers'''
        peers = ['peer_node/1', 'peer_node/2', 'peer_node/3']
        getenv.return_value = 'peer_node/1'
        self.assertTrue(cluster_utils.oldest_peer(peers))

    @patch('os.getenv')
    def test_is_not_oldest_peer(self, getenv):
        '''It detects local unit is not the oldest of all peers'''
        peers = ['peer_node/1', 'peer_node/2', 'peer_node/3']
        getenv.return_value = 'peer_node/2'
        self.assertFalse(cluster_utils.oldest_peer(peers))

    @patch.object(cluster_utils, 'is_crm_leader')
    @patch.object(cluster_utils, 'is_clustered')
    def test_is_elected_leader_clustered(self, is_clustered, is_crm_leader):
        '''It detects it is the eligible leader in a hacluster of units'''
        is_clustered.return_value = True
        is_crm_leader.return_value = True
        self.assertTrue(cluster_utils.is_elected_leader('vip'))

    @patch.object(cluster_utils, 'is_crm_leader')
    @patch.object(cluster_utils, 'is_clustered')
    def test_not_is_elected_leader_clustered(self, is_clustered, is_crm_leader):
        '''It detects it is not the eligible leader in a hacluster of units'''
        is_clustered.return_value = True
        is_crm_leader.return_value = False
        self.assertFalse(cluster_utils.is_elected_leader('vip'))

    @patch.object(cluster_utils, 'oldest_peer')
    @patch.object(cluster_utils, 'peer_units')
    @patch.object(cluster_utils, 'is_clustered')
    def test_is_is_elected_leader_unclustered(self, is_clustered,
                                              peer_units, oldest_peer):
        '''It detects it is the eligible leader in non-clustered peer group'''
        is_clustered.return_value = False
        oldest_peer.return_value = True
        self.assertTrue(cluster_utils.is_elected_leader('vip'))

    @patch.object(cluster_utils, 'oldest_peer')
    @patch.object(cluster_utils, 'peer_units')
    @patch.object(cluster_utils, 'is_clustered')
    def test_not_is_elected_leader_unclustered(self, is_clustered,
                                               peer_units, oldest_peer):
        '''It detects it is not the eligible leader in non-clustered group'''
        is_clustered.return_value = False
        oldest_peer.return_value = False
        self.assertFalse(cluster_utils.is_elected_leader('vip'))

    def test_https_explict(self):
        '''It determines https is available if configured explicitly'''
        # config_get('use-https')
        self.config_get.return_value = 'yes'
        self.assertTrue(cluster_utils.https())

    def test_https_cert_key_in_config(self):
        '''It determines https is available if cert + key in charm config'''
        # config_get('use-https')
        self.config_get.side_effect = [
            'no',  # config_get('use-https')
            'cert',  # config_get('ssl_cert')
            'key',  # config_get('ssl_key')
        ]
        self.assertTrue(cluster_utils.https())

    def test_https_cert_key_in_identity_relation(self):
        '''It determines https is available if cert in identity-service'''
        self.config_get.return_value = False
        self.relation_ids.return_value = 'identity-service:0'
        self.relation_list.return_value = 'keystone/0'
        self.relation_get.side_effect = [
            'yes',  # relation_get('https_keystone')
            'cert',  # relation_get('ssl_cert')
            'key',  # relation_get('ssl_key')
            'ca_cert',  # relation_get('ca_cert')
        ]
        self.assertTrue(cluster_utils.https())

    def test_https_cert_key_incomplete_identity_relation(self):
        '''It determines https unavailable if cert not in identity-service'''
        self.config_get.return_value = False
        self.relation_ids.return_value = 'identity-service:0'
        self.relation_list.return_value = 'keystone/0'
        self.relation_get.return_value = None
        self.assertFalse(cluster_utils.https())

    @patch.object(cluster_utils, 'https')
    @patch.object(cluster_utils, 'peer_units')
    def test_determine_api_port_with_peers(self, peer_units, https):
        '''It determines API port in presence of peers'''
        peer_units.return_value = ['peer1']
        https.return_value = False
        self.assertEquals(9686, cluster_utils.determine_api_port(9696))

    @patch.object(cluster_utils, 'https')
    @patch.object(cluster_utils, 'peer_units')
    def test_determine_api_port_nopeers_singlemode(self, peer_units, https):
        '''It determines API port with a single unit in singlemode'''
        peer_units.return_value = []
        https.return_value = False
        port = cluster_utils.determine_api_port(9696, singlenode_mode=True)
        self.assertEquals(9686, port)

    @patch.object(cluster_utils, 'is_clustered')
    @patch.object(cluster_utils, 'https')
    @patch.object(cluster_utils, 'peer_units')
    def test_determine_api_port_clustered(self, peer_units, https,
                                          is_clustered):
        '''It determines API port in presence of an hacluster'''
        peer_units.return_value = []
        is_clustered.return_value = True
        https.return_value = False
        self.assertEquals(9686, cluster_utils.determine_api_port(9696))

    @patch.object(cluster_utils, 'is_clustered')
    @patch.object(cluster_utils, 'https')
    @patch.object(cluster_utils, 'peer_units')
    def test_determine_api_port_clustered_https(self, peer_units, https,
                                                is_clustered):
        '''It determines API port in presence of hacluster + https'''
        peer_units.return_value = []
        is_clustered.return_value = True
        https.return_value = True
        self.assertEquals(9676, cluster_utils.determine_api_port(9696))

    @patch.object(cluster_utils, 'https')
    def test_determine_apache_port_https(self, https):
        '''It determines haproxy port with https enabled'''
        https.return_value = True
        self.assertEquals(9696, cluster_utils.determine_apache_port(9696))

    @patch.object(cluster_utils, 'https')
    @patch.object(cluster_utils, 'is_clustered')
    def test_determine_apache_port_clustered(self, https, is_clustered):
        '''It determines haproxy port with https disabled'''
        https.return_value = True
        is_clustered.return_value = True
        self.assertEquals(9686, cluster_utils.determine_apache_port(9696))

    @patch.object(cluster_utils, 'peer_units')
    @patch.object(cluster_utils, 'https')
    @patch.object(cluster_utils, 'is_clustered')
    def test_determine_apache_port_nopeers_singlemode(self, https,
                                                      is_clustered,
                                                      peer_units):
        '''It determines haproxy port with a single unit in singlemode'''
        peer_units.return_value = []
        https.return_value = False
        is_clustered.return_value = False
        port = cluster_utils.determine_apache_port(9696, singlenode_mode=True)
        self.assertEquals(9686, port)

    @patch.object(cluster_utils, 'valid_hacluster_config')
    def test_get_hacluster_config_complete(self, valid_hacluster_config):
        '''It fetches all hacluster charm config'''
        conf = {
            'ha-bindiface': 'eth1',
            'ha-mcastport': '3333',
            'vip': '10.0.0.1',
            'os-admin-hostname': None,
            'os-public-hostname': None,
            'os-internal-hostname': None,
            'os-access-hostname': None,
        }

        valid_hacluster_config.return_value = True

        def _fake_config_get(setting):
            return conf[setting]

        self.config_get.side_effect = _fake_config_get
        self.assertEquals(conf, cluster_utils.get_hacluster_config())

    @patch.object(cluster_utils, 'valid_hacluster_config')
    def test_get_hacluster_config_incomplete(self, valid_hacluster_config):
        '''It raises exception if some hacluster charm config missing'''
        conf = {
            'ha-bindiface': 'eth1',
            'ha-mcastport': '3333',
            'vip': None,
            'os-admin-hostname': None,
            'os-public-hostname': None,
            'os-internal-hostname': None,
            'os-access-hostname': None,
        }

        valid_hacluster_config.return_value = False

        def _fake_config_get(setting):
            return conf[setting]

        self.config_get.side_effect = _fake_config_get
        self.assertRaises(cluster_utils.HAIncorrectConfig,
                          cluster_utils.get_hacluster_config)

    @patch.object(cluster_utils, 'valid_hacluster_config')
    def test_get_hacluster_config_with_excludes(self, valid_hacluster_config):
        '''It fetches all hacluster charm config'''
        conf = {
            'ha-bindiface': 'eth1',
            'ha-mcastport': '3333',
        }
        valid_hacluster_config.return_value = True

        def _fake_config_get(setting):
            return conf[setting]

        self.config_get.side_effect = _fake_config_get
        exclude_keys = ['vip', 'os-admin-hostname', 'os-internal-hostname',
                        'os-public-hostname', 'os-access-hostname']
        result = cluster_utils.get_hacluster_config(exclude_keys)
        self.assertEquals(conf, result)

    @patch.object(cluster_utils, 'is_clustered')
    def test_canonical_url_bare(self, is_clustered):
        '''It constructs a URL to host with no https or cluster present'''
        self.unit_get.return_value = 'foohost1'
        is_clustered.return_value = False
        configs = MagicMock()
        configs.complete_contexts = MagicMock()
        configs.complete_contexts.return_value = []
        url = cluster_utils.canonical_url(configs)
        self.assertEquals('http://foohost1', url)

    @patch.object(cluster_utils, 'is_clustered')
    def test_canonical_url_https_no_cluster(self, is_clustered):
        '''It constructs a URL to host with https and no cluster present'''
        self.unit_get.return_value = 'foohost1'
        is_clustered.return_value = False
        configs = MagicMock()
        configs.complete_contexts = MagicMock()
        configs.complete_contexts.return_value = ['https']
        url = cluster_utils.canonical_url(configs)
        self.assertEquals('https://foohost1', url)

    @patch.object(cluster_utils, 'is_clustered')
    def test_canonical_url_https_cluster(self, is_clustered):
        '''It constructs a URL to host with https and cluster present'''
        self.config_get.return_value = '10.0.0.1'
        is_clustered.return_value = True
        configs = MagicMock()
        configs.complete_contexts = MagicMock()
        configs.complete_contexts.return_value = ['https']
        url = cluster_utils.canonical_url(configs)
        self.assertEquals('https://10.0.0.1', url)

    @patch.object(cluster_utils, 'is_clustered')
    def test_canonical_url_cluster_no_https(self, is_clustered):
        '''It constructs a URL to host with no https and cluster present'''
        self.config_get.return_value = '10.0.0.1'
        self.unit_get.return_value = 'foohost1'
        is_clustered.return_value = True
        configs = MagicMock()
        configs.complete_contexts = MagicMock()
        configs.complete_contexts.return_value = []
        url = cluster_utils.canonical_url(configs)
        self.assertEquals('http://10.0.0.1', url)

    @patch.object(cluster_utils, 'status_set')
    def test_valid_hacluster_config_incomplete(self, status_set):
        '''Returns False with incomplete HA config'''
        conf = {
            'vip': None,
            'os-admin-hostname': None,
            'os-public-hostname': None,
            'os-internal-hostname': None,
            'os-access-hostname': None,
            'dns-ha': False,
        }

        def _fake_config_get(setting):
            return conf[setting]

        self.config_get.side_effect = _fake_config_get
        self.assertRaises(cluster_utils.HAIncorrectConfig,
                          cluster_utils.valid_hacluster_config)

    @patch.object(cluster_utils, 'status_set')
    def test_valid_hacluster_config_both(self, status_set):
        '''Returns False when both VIP and DNS HA are set'''
        conf = {
            'vip': '10.0.0.1',
            'os-admin-hostname': None,
            'os-public-hostname': None,
            'os-internal-hostname': None,
            'os-access-hostname': None,
            'dns-ha': True,
        }

        def _fake_config_get(setting):
            return conf[setting]

        self.config_get.side_effect = _fake_config_get
        self.assertRaises(cluster_utils.HAIncorrectConfig,
                          cluster_utils.valid_hacluster_config)

    @patch.object(cluster_utils, 'status_set')
    def test_valid_hacluster_config_vip_ha(self, status_set):
        '''Returns True with complete VIP HA config'''
        conf = {
            'vip': '10.0.0.1',
            'os-admin-hostname': None,
            'os-public-hostname': None,
            'os-internal-hostname': None,
            'os-access-hostname': None,
            'dns-ha': False,
        }

        def _fake_config_get(setting):
            return conf[setting]

        self.config_get.side_effect = _fake_config_get
        self.assertTrue(cluster_utils.valid_hacluster_config())
        self.assertFalse(status_set.called)

    @patch.object(cluster_utils, 'status_set')
    def test_valid_hacluster_config_dns_incomplete(self, status_set):
        '''Returns False with incomplete DNS HA config'''
        conf = {
            'vip': None,
            'os-admin-hostname': None,
            'os-public-hostname': None,
            'os-internal-hostname': None,
            'os-access-hostname': None,
            'dns-ha': True,
        }

        def _fake_config_get(setting):
            return conf[setting]

        self.config_get.side_effect = _fake_config_get
        self.assertRaises(cluster_utils.HAIncompleteConfig,
                          cluster_utils.valid_hacluster_config)

    @patch.object(cluster_utils, 'status_set')
    def test_valid_hacluster_config_dns_ha(self, status_set):
        '''Returns True with complete DNS HA config'''
        conf = {
            'vip': None,
            'os-admin-hostname': 'somehostname',
            'os-public-hostname': None,
            'os-internal-hostname': None,
            'os-access-hostname': None,
            'dns-ha': True,
        }

        def _fake_config_get(setting):
            return conf[setting]

        self.config_get.side_effect = _fake_config_get
        self.assertTrue(cluster_utils.valid_hacluster_config())
        self.assertFalse(status_set.called)

    @patch.object(cluster_utils, 'juju_is_leader')
    @patch.object(cluster_utils, 'status_set')
    @patch.object(cluster_utils.time, 'sleep')
    @patch.object(cluster_utils, 'modulo_distribution')
    @patch.object(cluster_utils, 'log')
    def test_distributed_wait(self, log, modulo_distribution, sleep,
                              status_set, is_leader):

        # Leader regardless of modulo should not wait
        is_leader.return_value = True
        cluster_utils.distributed_wait(modulo=9, wait=23)
        modulo_distribution.assert_not_called()
        sleep.assert_called_with(0)

        # The rest of the tests are non-leader units
        is_leader.return_value = False

        def _fake_config_get(setting):
            return conf[setting]

        # Uses fallback defaults
        conf = {
            'modulo-nodes': None,
            'known-wait': None,
        }
        self.config_get.side_effect = _fake_config_get
        cluster_utils.distributed_wait()
        modulo_distribution.assert_called_with(modulo=3, wait=30,
                                               non_zero_wait=True)

        # Uses config values
        conf = {
            'modulo-nodes': 7,
            'known-wait': 10,
        }
        self.config_get.side_effect = _fake_config_get
        cluster_utils.distributed_wait()
        modulo_distribution.assert_called_with(modulo=7, wait=10,
                                               non_zero_wait=True)

        # Uses passed values
        cluster_utils.distributed_wait(modulo=5, wait=45)
        modulo_distribution.assert_called_with(modulo=5, wait=45,
                                               non_zero_wait=True)

    @patch.object(cluster_utils, 'relation_ids')
    def test_get_managed_services_and_ports(self, relation_ids):
        relation_ids.return_value = ['rel:2']
        self.assertEqual(
            cluster_utils.get_managed_services_and_ports(
                ['apache2', 'haproxy'],
                [8067, 4545, 6732]),
            (['apache2'], [8057, 4535, 6722]))
        self.assertEqual(
            cluster_utils.get_managed_services_and_ports(
                ['apache2', 'haproxy'],
                [8067, 4545, 6732],
                external_services=['apache2']),
            (['haproxy'], [8057, 4535, 6722]))

        def add_ten(x):
            return x + 10

        self.assertEqual(
            cluster_utils.get_managed_services_and_ports(
                ['apache2', 'haproxy'],
                [8067, 4545, 6732],
                port_conv_f=add_ten),
            (['apache2'], [8077, 4555, 6742]))
