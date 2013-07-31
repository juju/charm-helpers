
from mock import patch, MagicMock

from subprocess import CalledProcessError
from testtools import TestCase

import charmhelpers.contrib.hahelpers.cluster as cluster_utils


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
    def test_is_leader(self, check_output):
        '''It determines its unit is leader'''
        self.get_unit_hostname.return_value = 'node1'
        crm = 'resource vip is running on: node1'
        check_output.return_value = crm
        self.assertTrue(cluster_utils.is_leader('vip'))

    @patch('subprocess.check_output')
    def test_is_not_leader(self, check_output):
        '''It determines its unit is not leader'''
        self.get_unit_hostname.return_value = 'node1'
        crm = 'resource vip is running on: node2'
        check_output.return_value = crm
        self.assertFalse(cluster_utils.is_leader('some_resource'))

    @patch('subprocess.check_output')
    def test_is_leader_no_cluster(self, check_output):
        '''It is not leader if there is no cluster up'''
        check_output.side_effect = CalledProcessError(1, 'crm')
        self.assertFalse(cluster_utils.is_leader('vip'))

    def test_peer_units(self):
        '''It lists all peer units for cluster relation'''
        peers = ['peer_node/1', 'peer_node/2']
        self.relation_ids.return_value = ['cluster:0']
        self.relation_list.return_value = peers
        self.assertEquals(peers, cluster_utils.peer_units())

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

    @patch.object(cluster_utils, 'is_leader')
    @patch.object(cluster_utils, 'is_clustered')
    def test_is_eligible_leader_clustered(self, is_clustered, is_leader):
        '''It detects it is the eligible leader in a hacluster of units'''
        is_clustered.return_value = True
        is_leader.return_value = True
        self.assertTrue(cluster_utils.eligible_leader('vip'))

    @patch.object(cluster_utils, 'is_leader')
    @patch.object(cluster_utils, 'is_clustered')
    def test_not_eligible_leader_clustered(self, is_clustered, is_leader):
        '''It detects it is not the eligible leader in a hacluster of units'''
        is_clustered.return_value = True
        is_leader.return_value = False
        self.assertFalse(cluster_utils.eligible_leader('vip'))

    @patch.object(cluster_utils, 'oldest_peer')
    @patch.object(cluster_utils, 'peer_units')
    @patch.object(cluster_utils, 'is_clustered')
    def test_is_eligible_leader_unclustered(self, is_clustered,
                                            peer_units, oldest_peer):
        '''It detects it is the eligible leader in non-clustered peer group'''
        is_clustered.return_value = False
        oldest_peer.return_value = True
        self.assertTrue(cluster_utils.eligible_leader('vip'))

    @patch.object(cluster_utils, 'oldest_peer')
    @patch.object(cluster_utils, 'peer_units')
    @patch.object(cluster_utils, 'is_clustered')
    def test_not_eligible_leader_unclustered(self, is_clustered,
                                             peer_units, oldest_peer):
        '''It detects it is not the eligible leader in non-clustered group'''
        is_clustered.return_value = False
        oldest_peer.return_value = False
        self.assertFalse(cluster_utils.eligible_leader('vip'))

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
    def test_determine_haproxy_port_https(self, https):
        '''It determines haproxy port with https enabled'''
        https.return_value = True
        self.assertEquals(9686, cluster_utils.determine_haproxy_port(9696))

    @patch.object(cluster_utils, 'https')
    def test_determine_haproxy_port_no_https(self, https):
        '''It determines haproxy port with https disabled'''
        https.return_value = False
        self.assertEquals(9696, cluster_utils.determine_haproxy_port(9696))

    def test_get_hacluster_config_complete(self):
        '''It fetches all hacluster charm config'''
        conf = {
            'ha-bindiface': 'eth1',
            'ha-mcastport': '3333',
            'vip': '10.0.0.1',
            'vip_iface': 'eth1',
            'vip_cidr': '19'
        }

        def _fake_config_get(setting):
            return conf[setting]

        self.config_get.side_effect = _fake_config_get
        self.assertEquals(conf, cluster_utils.get_hacluster_config())

    def test_get_hacluster_config_incomplete(self):
        '''It raises exception if some hacluster charm config missing'''
        conf = {
            'ha-bindiface': 'eth1',
            'ha-mcastport': '3333',
            'vip': None,
            'vip_iface': 'eth1',
            'vip_cidr': '19'
        }

        def _fake_config_get(setting):
            return conf[setting]

        self.config_get.side_effect = _fake_config_get
        self.assertRaises(cluster_utils.HAIncompleteConfig,
                          cluster_utils.get_hacluster_config)

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
