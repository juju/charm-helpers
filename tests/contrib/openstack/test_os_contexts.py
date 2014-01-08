import yaml
import json
import unittest

from tests.helpers import patch_open

from mock import patch, MagicMock, call

from copy import copy

import charmhelpers.contrib.openstack.context as context


class FakeRelation(object):
    '''
    A fake relation class. Lets tests specify simple relation data
    for a default relation + unit (foo:0, foo/0, set in setUp()), eg:

        rel = {
            'private-address': 'foo',
            'password': 'passwd',
        }
        relation = FakeRelation(rel)
        self.relation_get.side_effect = relation.get
        passwd = self.relation_get('password')

    or more complex relations meant to be addressed by explicit relation id
    + unit id combos:

        rel = {
            'mysql:0': {
                'mysql/0': {
                    'private-address': 'foo',
                    'password': 'passwd',
                }
            }
        }
        relation = FakeRelation(rel)
        self.relation_get.side_affect = relation.get
        passwd = self.relation_get('password', rid='mysql:0', unit='mysql/0')
    '''
    def __init__(self, relation_data):
        self.relation_data = relation_data

    def get(self, attr=None, unit=None, rid=None):
        if not rid or rid == 'foo:0':
            if attr is None:
                return self.relation_data
            elif attr in self.relation_data:
                return self.relation_data[attr]
            return None
        else:
            if rid not in self.relation_data:
                return None
            try:
                relation = self.relation_data[rid][unit]
            except KeyError:
                return None
            if attr in relation:
                return relation[attr]
            return None

    def relation_ids(self, relation):
        return self.relation_data.keys()

    def relation_units(self, relation_id):
        if relation_id not in self.relation_data:
            return None
        return self.relation_data[relation_id].keys()

SHARED_DB_RELATION = {
    'db_host': 'dbserver.local',
    'password': 'foo',
}

SHARED_DB_CONFIG = {
    'database-user': 'adam',
    'database': 'foodb',
}

IDENTITY_SERVICE_RELATION = {
    'service_port': '5000',
    'service_host': 'keystonehost.local',
    'auth_host': 'keystone-host.local',
    'auth_port': '35357',
    'service_tenant': 'admin',
    'service_password': 'foo',
    'service_username': 'adam',
}

AMQP_RELATION = {
    'private-address': 'rabbithost',
    'password': 'foobar',
    'vip': '10.0.0.1',
}

AMQP_AA_RELATION = {
    'amqp:0': {
        'rabbitmq/0': {
            'private-address': 'rabbithost1',
            'password': 'foobar',
        },
        'rabbitmq/1': {
            'private-address': 'rabbithost2',
        }
    }
}

AMQP_CONFIG = {
    'rabbit-user': 'adam',
    'rabbit-vhost': 'foo',
}

CEPH_RELATION = {
    'ceph:0': {
        'ceph/0': {
            'private-address': 'ceph_node1',
            'auth': 'foo',
            'key': 'bar',
        },
        'ceph/1': {
            'private-address': 'ceph_node2',
            'auth': 'foo',
            'key': 'bar',
        },
    }
}

SUB_CONFIG = """
nova:
    /etc/nova/nova.conf:
        sections:
            DEFAULT:
                - [nova-key1, value1]
                - [nova-key2, value2]
glance:
    /etc/glance/glance.conf:
        sections:
            DEFAULT:
                - [glance-key1, value1]
                - [glance-key2, value2]
"""

SUB_CONFIG_RELATION = {
    'nova-subordinate:0': {
        'nova-subordinate/0': {
            'private-address': 'nova_node1',
            'subordinate_configuration': json.dumps(yaml.load(SUB_CONFIG)),
        },
    },
    'glance-subordinate:0': {
        'glance-subordinate/0': {
            'private-address': 'glance_node1',
            'subordinate_configuration': json.dumps(yaml.load(SUB_CONFIG)),
        },
    },
    'foo-subordinate:0': {
        'foo-subordinate/0': {
            'private-address': 'foo_node1',
            'subordinate_configuration': 'ea8e09324jkadsfh',
        },
    }
}

# Imported in contexts.py and needs patching in setUp()
TO_PATCH = [
    'b64decode',
    'check_call',
    'get_cert',
    'get_ca_cert',
    'log',
    'config',
    'relation_get',
    'relation_ids',
    'related_units',
    'unit_get',
    'https',
    'determine_api_port',
    'determine_haproxy_port',
    'peer_units',
    'is_clustered',
]


class fake_config(object):
    def __init__(self, data):
        self.data = data

    def __call__(self, attr):
        if attr in self.data:
            return self.data[attr]
        return None


class ContextTests(unittest.TestCase):
    def setUp(self):
        for m in TO_PATCH:
            setattr(self, m, self._patch(m))
        # mock at least a single relation + unit
        self.relation_ids.return_value = ['foo:0']
        self.related_units.return_value = ['foo/0']

    def _patch(self, method):
        _m = patch('charmhelpers.contrib.openstack.context.' + method)
        mock = _m.start()
        self.addCleanup(_m.stop)
        return mock

    def test_base_class_not_implemented(self):
        base = context.OSContextGenerator()
        self.assertRaises(NotImplementedError, base)

    def test_shared_db_context_with_data(self):
        '''Test shared-db context with all required data'''
        relation = FakeRelation(relation_data=SHARED_DB_RELATION)
        self.relation_get.side_effect = relation.get
        self.config.side_effect = fake_config(SHARED_DB_CONFIG)
        shared_db = context.SharedDBContext()
        result = shared_db()
        expected = {
            'database_host': 'dbserver.local',
            'database': 'foodb',
            'database_user': 'adam',
            'database_password': 'foo',
        }
        self.assertEquals(result, expected)

    def test_shared_db_context_with_missing_relation(self):
        '''Test shared-db context missing relation data'''
        incomplete_relation = copy(SHARED_DB_RELATION)
        incomplete_relation['password'] = None
        relation = FakeRelation(relation_data=incomplete_relation)
        self.relation_get.side_effect = relation.get
        self.config.return_value = SHARED_DB_CONFIG
        shared_db = context.SharedDBContext()
        result = shared_db()
        self.assertEquals(result, {})

    def test_shared_db_context_with_missing_config(self):
        '''Test shared-db context missing relation data'''
        incomplete_config = copy(SHARED_DB_CONFIG)
        del incomplete_config['database-user']
        self.config.side_effect = fake_config(incomplete_config)
        relation = FakeRelation(relation_data=SHARED_DB_RELATION)
        self.relation_get.side_effect = relation.get
        self.config.return_value = incomplete_config
        shared_db = context.SharedDBContext()
        self.assertRaises(context.OSContextError, shared_db)

    def test_shared_db_context_with_params(self):
        '''Test shared-db context with object parameters'''
        shared_db = context.SharedDBContext(
            database='quantum', user='quantum', relation_prefix='quantum')
        result = shared_db()
        self.assertIn(call('quantum_password', rid='foo:0', unit='foo/0'),
                      self.relation_get.call_args_list)
        self.assertEquals(result['database'], 'quantum')
        self.assertEquals(result['database_user'], 'quantum')

    def test_identity_service_context_with_data(self):
        '''Test shared-db context with all required data'''
        relation = FakeRelation(relation_data=IDENTITY_SERVICE_RELATION)
        self.relation_get.side_effect = relation.get
        identity_service = context.IdentityServiceContext()
        result = identity_service()
        expected = {
            'admin_password': 'foo',
            'admin_tenant_name': 'admin',
            'admin_user': 'adam',
            'auth_host': 'keystone-host.local',
            'auth_port': '35357',
            'auth_protocol': 'http',
            'service_host': 'keystonehost.local',
            'service_port': '5000',
            'service_protocol': 'http'
        }
        self.assertEquals(result, expected)

    def test_identity_service_context_with_missing_relation(self):
        '''Test shared-db context missing relation data'''
        incomplete_relation = copy(IDENTITY_SERVICE_RELATION)
        incomplete_relation['service_password'] = None
        relation = FakeRelation(relation_data=incomplete_relation)
        self.relation_get.side_effect = relation.get
        identity_service = context.IdentityServiceContext()
        result = identity_service()
        self.assertEquals(result, {})

    def test_amqp_context_with_data(self):
        '''Test amqp context with all required data'''
        relation = FakeRelation(relation_data=AMQP_RELATION)
        self.relation_get.side_effect = relation.get
        self.config.return_value = AMQP_CONFIG
        amqp = context.AMQPContext()
        result = amqp()
        expected = {
            'rabbitmq_host': 'rabbithost',
            'rabbitmq_password': 'foobar',
            'rabbitmq_user': 'adam',
            'rabbitmq_virtual_host': 'foo'
        }
        self.assertEquals(result, expected)

    def test_amqp_context_with_data_clustered(self):
        '''Test amqp context with all required data with clustered rabbit'''
        relation_data = copy(AMQP_RELATION)
        relation_data['clustered'] = 'yes'
        relation = FakeRelation(relation_data=relation_data)
        self.relation_get.side_effect = relation.get
        self.config.return_value = AMQP_CONFIG
        amqp = context.AMQPContext()
        result = amqp()
        expected = {
            'clustered': True,
            'rabbitmq_host': relation_data['vip'],
            'rabbitmq_password': 'foobar',
            'rabbitmq_user': 'adam',
            'rabbitmq_virtual_host': 'foo',
        }
        self.assertEquals(result, expected)

    def test_amqp_context_with_data_active_active(self):
        '''Test amqp context with required data with active/active rabbit'''
        relation_data = copy(AMQP_AA_RELATION)
        relation = FakeRelation(relation_data=relation_data)
        self.relation_get.side_effect = relation.get
        self.relation_ids.side_effect = relation.relation_ids
        self.related_units.side_effect = relation.relation_units
        self.config.return_value = AMQP_CONFIG
        amqp = context.AMQPContext()
        result = amqp()
        expected = {
            'rabbitmq_host': 'rabbithost1',
            'rabbitmq_password': 'foobar',
            'rabbitmq_user': 'adam',
            'rabbitmq_virtual_host': 'foo',
            'rabbitmq_hosts': 'rabbithost2,rabbithost1',
        }
        self.assertEquals(result, expected)

    def test_amqp_context_with_missing_relation(self):
        '''Test amqp context missing relation data'''
        incomplete_relation = copy(AMQP_RELATION)
        incomplete_relation['password'] = ''
        relation = FakeRelation(relation_data=incomplete_relation)
        self.relation_get.side_effect = relation.get
        self.config.return_value = AMQP_CONFIG
        amqp = context.AMQPContext()
        result = amqp()
        self.assertEquals({}, result)

    def test_amqp_context_with_missing_config(self):
        '''Test amqp context missing relation data'''
        incomplete_config = copy(AMQP_CONFIG)
        del incomplete_config['rabbit-user']
        relation = FakeRelation(relation_data=AMQP_RELATION)
        self.relation_get.side_effect = relation.get
        self.config.return_value = incomplete_config
        amqp = context.AMQPContext()
        self.assertRaises(context.OSContextError, amqp)

    @patch('os.path.isdir')
    @patch('os.mkdir')
    @patch.object(context, 'ensure_packages')
    def test_ceph_context_with_data(self, ensure_packages, mkdir, isdir):
        '''Test ceph context with all relation data'''
        isdir.return_value = False
        relation = FakeRelation(relation_data=CEPH_RELATION)
        self.relation_get.side_effect = relation.get
        self.relation_ids.side_effect = relation.relation_ids
        self.related_units.side_effect = relation.relation_units
        ceph = context.CephContext()
        result = ceph()
        expected = {
            'mon_hosts': 'ceph_node2 ceph_node1',
            'auth': 'foo',
            'key': 'bar',
        }
        self.assertEquals(result, expected)
        ensure_packages.assert_called_with(['ceph-common'])
        mkdir.assert_called_with('/etc/ceph')

    @patch('os.mkdir')
    @patch.object(context, 'ensure_packages')
    def test_ceph_context_with_missing_data(self, ensure_packages, mkdir):
        '''Test ceph context with missing relation data'''
        relation = copy(CEPH_RELATION)
        for k, v in relation.iteritems():
            for u in v.iterkeys():
                del relation[k][u]['auth']
        relation = FakeRelation(relation_data=relation)
        self.relation_get.side_effect = relation.get
        self.relation_ids.side_effect = relation.relation_ids
        self.related_units.side_effect = relation.relation_units
        ceph = context.CephContext()
        result = ceph()
        self.assertEquals(result, {})
        self.assertFalse(ensure_packages.called)

    @patch('charmhelpers.contrib.openstack.context.unit_get')
    @patch('charmhelpers.contrib.openstack.context.local_unit')
    def test_haproxy_context_with_data(self, local_unit, unit_get):
        '''Test haproxy context with all relation data'''
        cluster_relation = {
            'cluster:0': {
                'peer/1': {
                    'private-address': 'cluster-peer1.localnet',
                },
                'peer/2': {
                    'private-address': 'cluster-peer2.localnet',
                },
            },
        }
        local_unit.return_value = 'peer/0'
        unit_get.return_value = 'cluster-peer0.localnet'
        relation = FakeRelation(cluster_relation)
        self.relation_ids.side_effect = relation.relation_ids
        self.relation_get.side_effect = relation.get
        self.related_units.side_effect = relation.relation_units
        haproxy = context.HAProxyContext()
        with patch_open() as (_open, _file):
            result = haproxy()
        ex = {
            'units': {
                'peer-0': 'cluster-peer0.localnet',
                'peer-1': 'cluster-peer1.localnet',
                'peer-2': 'cluster-peer2.localnet'
            }
        }
        # the context gets generated.
        self.assertEquals(ex, result)
        # and /etc/default/haproxy is updated.
        self.assertEquals(_file.write.call_args_list,
                          [call('ENABLED=1\n')])

    def test_haproxy_context_with_missing_data(self):
        '''Test haproxy context with missing relation data'''
        self.relation_ids.return_value = []
        haproxy = context.HAProxyContext()
        self.assertEquals({}, haproxy())

    @patch('charmhelpers.contrib.openstack.context.unit_get')
    @patch('charmhelpers.contrib.openstack.context.local_unit')
    def test_haproxy_context_with_no_peers(self, local_unit, unit_get):
        '''Test haproxy context with single unit'''
        # peer relations always show at least one peer relation, even
        # if unit is alone. should be an incomplete context.
        cluster_relation = {
            'cluster:0': {
                'peer/0': {
                    'private-address': 'lonely.clusterpeer.howsad',
                },
            },
        }
        local_unit.return_value = 'peer/0'
        unit_get.return_value = 'lonely.clusterpeer.howsad'
        relation = FakeRelation(cluster_relation)
        self.relation_ids.side_effect = relation.relation_ids
        self.relation_get.side_effect = relation.get
        self.related_units.side_effect = relation.relation_units
        haproxy = context.HAProxyContext()
        self.assertEquals({}, haproxy())

    def test_https_context_with_no_https(self):
        '''Test apache2 https when no https data available'''
        apache = context.ApacheSSLContext()
        self.https.return_value = False
        self.assertEquals({}, apache())

    def _test_https_context(self, apache, is_clustered, peer_units):
        self.https.return_value = True

        if is_clustered or peer_units:
            self.determine_api_port.return_value = 8756
            self.determine_haproxy_port.return_value = 8766
        else:
            self.determine_api_port.return_value = 8766

        self.unit_get.return_value = 'cinderhost1'
        self.is_clustered.return_value = is_clustered
        self.peer_units.return_value = peer_units
        apache = context.ApacheSSLContext()
        apache.configure_cert = MagicMock
        apache.enable_modules = MagicMock
        apache.external_ports = '8776'
        apache.service_namespace = 'cinder'

        ex = {
            'private_address': 'cinderhost1',
            'namespace': 'cinder',
            'endpoints': [(8776, 8766)],
        }
        self.assertEquals(ex, apache())
        self.assertTrue(apache.configure_cert.called)
        self.assertTrue(apache.enable_modules.called)

    def test_https_context_no_peers_no_cluster(self):
        '''Test apache2 https on a single, unclustered unit'''
        apache = context.ApacheSSLContext()
        self._test_https_context(apache, is_clustered=False, peer_units=None)

    def test_https_context_wth_peers_no_cluster(self):
        '''Test apache2 https on a unclustered unit with peers'''
        apache = context.ApacheSSLContext()
        self._test_https_context(apache, is_clustered=False, peer_units=[1, 2])

    def test_https_context_loads_correct_apache_mods(self):
        '''Test apache2 context also loads required apache modules'''
        apache = context.ApacheSSLContext()
        apache.enable_modules()
        ex_cmd = ['a2enmod', 'ssl', 'proxy', 'proxy_http']
        self.check_call.assert_called_with(ex_cmd)

    @patch('__builtin__.open')
    @patch('os.mkdir')
    @patch('os.path.isdir')
    def test_https_configure_cert(self, isdir, mkdir, _open):
        '''Test apache2 properly installs certs and keys to disk'''
        isdir.return_value = False
        self.get_cert.return_value = ('SSL_CERT', 'SSL_KEY')
        self.get_ca_cert.return_value = 'CA_CERT'
        apache = context.ApacheSSLContext()
        apache.service_namespace = 'cinder'
        apache.configure_cert()
        # appropriate directories are created.
        dirs = [call('/etc/apache2/ssl'), call('/etc/apache2/ssl/cinder')]
        self.assertEquals(dirs, mkdir.call_args_list)
        # appropriate files are opened for writing.
        _ca = '/usr/local/share/ca-certificates/keystone_juju_ca_cert.crt'
        files = [call('/etc/apache2/ssl/cinder/cert', 'w'),
                 call('/etc/apache2/ssl/cinder/key', 'w'),
                 call(_ca, 'w')]
        for f in files:
            self.assertIn(f, _open.call_args_list)
        # appropriate bits are b64decoded.
        decode = [call('SSL_CERT'), call('SSL_KEY'), call('CA_CERT')]
        self.assertEquals(decode, self.b64decode.call_args_list)

    def test_image_service_context_missing_data(self):
        '''Test image-service with missing relation and missing data'''
        image_service = context.ImageServiceContext()
        self.relation_ids.return_value = []
        self.assertEquals({}, image_service())
        self.relation_ids.return_value = ['image-service:0']
        self.related_units.return_value = ['glance/0']
        self.relation_get.return_value = None
        self.assertEquals({}, image_service())

    def test_image_service_context_with_data(self):
        '''Test image-service with required data'''
        image_service = context.ImageServiceContext()
        self.relation_ids.return_value = ['image-service:0']
        self.related_units.return_value = ['glance/0']
        self.relation_get.return_value = 'http://glancehost:9292'
        self.assertEquals({'glance_api_servers': 'http://glancehost:9292'},
                          image_service())

    @patch.object(context, 'neutron_plugin_attribute')
    def test_neutron_context_base_properties(self, attr):
        '''Test neutron context base properties'''
        neutron = context.NeutronContext()
        attr.return_value = 'quantum-plugin-package'
        self.assertEquals(None, neutron.plugin)
        self.assertEquals(None, neutron.network_manager)
        self.assertEquals(None, neutron.neutron_security_groups)
        self.assertEquals('quantum-plugin-package', neutron.packages)

    @patch.object(context, 'neutron_plugin_attribute')
    @patch.object(context, 'apt_install')
    @patch.object(context, 'filter_installed_packages')
    def test_neutron_ensure_package(self, _filter, _install, _packages):
        '''Test neutron context installed required packages'''
        _filter.return_value = ['quantum-plugin-package']
        _packages.return_value = [['quantum-plugin-package']]
        neutron = context.NeutronContext()
        neutron._ensure_packages()
        _install.assert_called_with(['quantum-plugin-package'], fatal=True)

    @patch.object(context.NeutronContext, 'network_manager')
    @patch.object(context.NeutronContext, 'plugin')
    def test_neutron_save_flag_file(self, plugin, nm):
        neutron = context.NeutronContext()
        plugin.__get__ = MagicMock(return_value='ovs')
        nm.__get__ = MagicMock(return_value='quantum')
        with patch_open() as (_o, _f):
            neutron._save_flag_file()
            _o.assert_called_with('/etc/nova/quantum_plugin.conf', 'wb')
            _f.write.assert_called_with('ovs\n')

        nm.__get__ = MagicMock(return_value='neutron')
        with patch_open() as (_o, _f):
            neutron._save_flag_file()
            _o.assert_called_with('/etc/nova/neutron_plugin.conf', 'wb')
            _f.write.assert_called_with('ovs\n')

    @patch.object(context.NeutronContext, 'neutron_security_groups')
    @patch.object(context, 'unit_private_ip')
    @patch.object(context, 'neutron_plugin_attribute')
    def test_neutron_ovs_plugin_context(self, attr, ip, sec_groups):
        ip.return_value = '10.0.0.1'
        sec_groups.__get__ = MagicMock(return_value=True)
        attr.return_value = 'some.quantum.driver.class'
        neutron = context.NeutronContext()
        self.assertEquals({
            'config': 'some.quantum.driver.class',
            'core_plugin': 'some.quantum.driver.class',
            'neutron_plugin': 'ovs',
            'neutron_security_groups': True,
            'local_ip': '10.0.0.1'}, neutron.ovs_ctxt())

    @patch.object(context.NeutronContext, '_save_flag_file')
    @patch.object(context.NeutronContext, 'ovs_ctxt')
    @patch.object(context.NeutronContext, 'plugin')
    @patch.object(context.NeutronContext, '_ensure_packages')
    @patch.object(context.NeutronContext, 'network_manager')
    def test_neutron_main_context_generation(self, nm, pkgs, plugin, ovs, ff):
        neutron = context.NeutronContext()
        nm.__get__ = MagicMock(return_value='flatdhcpmanager')
        self.assertEquals({}, neutron())

        nm.__get__ = MagicMock(return_value='neutron')
        plugin.__get__ = MagicMock(return_value=None)
        self.assertEquals({}, neutron())

        nm.__get__ = MagicMock(return_value='neutron')
        ovs.return_value = {'ovs': 'ovs_context'}
        plugin.__get__ = MagicMock(return_value='ovs')
        self.assertEquals(
            {'network_manager': 'neutron', 'ovs': 'ovs_context'},
            neutron()
        )

    @patch.object(context, 'config')
    def test_os_configflag_context(self, config):
        flags = context.OSConfigFlagContext()

        # single
        config.return_value = 'deadbeef=True'
        self.assertEquals({
            'user_config_flags': {
                'deadbeef': 'True',
            }
        }, flags())

        # multi
        config.return_value = 'floating_ip=True,use_virtio=False,max=5'
        self.assertEquals({
            'user_config_flags': {
                'floating_ip': 'True',
                'use_virtio': 'False',
                'max': '5',
            }
        }, flags())

        for empty in [None, '']:
            config.return_value = empty
            self.assertEquals({}, flags())

        # multi with commas
        config.return_value = 'good_flag=woot,badflag,great_flag=w00t'
        self.assertEquals({
            'user_config_flags': {
                'good_flag': 'woot,badflag',
                'great_flag': 'w00t',
            }
        }, flags())

        # missing key
        config.return_value = 'good_flag=woot=toow'
        self.assertRaises(context.OSContextError, flags)

        # bad value
        config.return_value = 'good_flag=woot=='
        self.assertRaises(context.OSContextError, flags)

    def test_os_subordinate_config_context(self):
        relation = FakeRelation(relation_data=SUB_CONFIG_RELATION)
        self.relation_get.side_effect = relation.get
        self.relation_ids.side_effect = relation.relation_ids
        self.related_units.side_effect = relation.relation_units
        nova_sub_ctxt = context.SubordinateConfigContext(
            service='nova',
            config_file='/etc/nova/nova.conf',
            interface='nova-subordinate',
        )
        glance_sub_ctxt = context.SubordinateConfigContext(
            service='glance',
            config_file='/etc/glance/glance.conf',
            interface='glance-subordinate',
        )
        foo_sub_ctxt = context.SubordinateConfigContext(
            service='foo',
            config_file='/etc/foo/foo.conf',
            interface='foo-subordinate',
        )
        self.assertEquals(
            nova_sub_ctxt(),
            {'sections': {
                'DEFAULT': [
                    ['nova-key1', 'value1'],
                    ['nova-key2', 'value2']]
                }}
        )
        self.assertEquals(
            glance_sub_ctxt(),
            {'sections': {
                'DEFAULT': [
                    ['glance-key1', 'value1'],
                    ['glance-key2', 'value2']]
                }}
        )

        # subrodinate supplies nothing for given config
        glance_sub_ctxt.config_file = '/etc/glance/glance-api-paste.ini'
        self.assertEquals(glance_sub_ctxt(), {'sections': {}})

        # subordinate supplies bad input
        self.assertEquals(foo_sub_ctxt(), {'sections': {}})
