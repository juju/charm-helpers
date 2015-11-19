import charmhelpers.contrib.openstack.context as context
import yaml
import json
import unittest
from copy import copy, deepcopy
from mock import (
    patch,
    Mock,
    MagicMock,
    call
)
from tests.helpers import patch_open

import six

if not six.PY3:
    open_builtin = '__builtin__.open'
else:
    open_builtin = 'builtins.open'


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

    def get(self, attribute=None, unit=None, rid=None):
        if not rid or rid == 'foo:0':
            if attribute is None:
                return self.relation_data
            elif attribute in self.relation_data:
                return self.relation_data[attribute]
            return None
        else:
            if rid not in self.relation_data:
                return None
            try:
                relation = self.relation_data[rid][unit]
            except KeyError:
                return None
            if attribute is None:
                return relation
            if attribute in relation:
                return relation[attribute]
            return None

    def relation_ids(self, relation):
        rids = []
        for rid in sorted(self.relation_data.keys()):
            if relation + ':' in rid:
                rids.append(rid)
        return rids

    def relation_units(self, relation_id):
        if relation_id not in self.relation_data:
            return None
        return sorted(self.relation_data[relation_id].keys())

SHARED_DB_RELATION = {
    'db_host': 'dbserver.local',
    'password': 'foo'
}

SHARED_DB_RELATION_SSL = {
    'db_host': 'dbserver.local',
    'password': 'foo',
    'ssl_ca': 'Zm9vCg==',
    'ssl_cert': 'YmFyCg==',
    'ssl_key': 'Zm9vYmFyCg==',
}

SHARED_DB_CONFIG = {
    'database-user': 'adam',
    'database': 'foodb',
}

SHARED_DB_RELATION_NAMESPACED = {
    'db_host': 'bar',
    'quantum_password': 'bar2'
}

SHARED_DB_RELATION_ACCESS_NETWORK = {
    'db_host': 'dbserver.local',
    'password': 'foo',
    'access-network': '10.5.5.0/24',
    'hostname': 'bar',
}


IDENTITY_SERVICE_RELATION_HTTP = {
    'service_port': '5000',
    'service_host': 'keystonehost.local',
    'auth_host': 'keystone-host.local',
    'auth_port': '35357',
    'service_tenant': 'admin',
    'service_tenant_id': '123456',
    'service_password': 'foo',
    'service_username': 'adam',
    'service_protocol': 'http',
    'auth_protocol': 'http',
}

IDENTITY_SERVICE_RELATION_UNSET = {
    'service_port': '5000',
    'service_host': 'keystonehost.local',
    'auth_host': 'keystone-host.local',
    'auth_port': '35357',
    'service_tenant': 'admin',
    'service_password': 'foo',
    'service_username': 'adam',
}

APIIDENTITY_SERVICE_RELATION_UNSET = {
    'neutron-plugin-api:0': {
        'neutron-api/0': {
            'service_port': '5000',
            'service_host': 'keystonehost.local',
            'auth_host': 'keystone-host.local',
            'auth_port': '35357',
            'service_tenant': 'admin',
            'service_password': 'foo',
            'service_username': 'adam',
        }
    }
}

IDENTITY_SERVICE_RELATION_HTTPS = {
    'service_port': '5000',
    'service_host': 'keystonehost.local',
    'auth_host': 'keystone-host.local',
    'auth_port': '35357',
    'service_tenant': 'admin',
    'service_password': 'foo',
    'service_username': 'adam',
    'service_protocol': 'https',
    'auth_protocol': 'https',
}

POSTGRESQL_DB_RELATION = {
    'host': 'dbserver.local',
    'user': 'adam',
    'password': 'foo',
}

POSTGRESQL_DB_CONFIG = {
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

AMQP_RELATION_WITH_SSL = {
    'private-address': 'rabbithost',
    'password': 'foobar',
    'vip': '10.0.0.1',
    'ssl_port': 5671,
    'ssl_ca': 'cert',
    'ha_queues': 'queues',
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

AMQP_OSLO_CONFIG = {
    'oslo-messaging-flags': "rabbit_max_retries=1,rabbit_retry_backoff=1,rabbit_retry_interval=1"
}

AMQP_NOVA_CONFIG = {
    'nova-rabbit-user': 'adam',
    'nova-rabbit-vhost': 'foo',
}

HAPROXY_CONFIG = {
    'haproxy-server-timeout': 50000,
    'haproxy-client-timeout': 50000,
}

CEPH_RELATION = {
    'ceph:0': {
        'ceph/0': {
            'private-address': 'ceph_node1',
            'auth': 'foo',
            'key': 'bar',
            'use_syslog': 'true',
        },
        'ceph/1': {
            'private-address': 'ceph_node2',
            'auth': 'foo',
            'key': 'bar',
            'use_syslog': 'false',
        },
    }
}

CEPH_RELATION_WITH_PUBLIC_ADDR = {
    'ceph:0': {
        'ceph/0': {
            'ceph-public-address': '192.168.1.10',
            'private-address': 'ceph_node1',
            'auth': 'foo',
            'key': 'bar',
        },
        'ceph/1': {
            'ceph-public-address': '192.168.1.11',
            'private-address': 'ceph_node2',
            'auth': 'foo',
            'key': 'bar',
        },
    }
}

IDENTITY_RELATION_NO_CERT = {
    'identity-service:0': {
        'keystone/0': {
            'private-address': 'keystone1',
        },
    }
}

IDENTITY_RELATION_SINGLE_CERT = {
    'identity-service:0': {
        'keystone/0': {
            'private-address': 'keystone1',
            'ssl_cert_cinderhost1': 'certa',
            'ssl_key_cinderhost1': 'keya',
        },
    }
}

IDENTITY_RELATION_MULTIPLE_CERT = {
    'identity-service:0': {
        'keystone/0': {
            'private-address': 'keystone1',
            'ssl_cert_cinderhost1-int-network': 'certa',
            'ssl_key_cinderhost1-int-network': 'keya',
            'ssl_cert_cinderhost1-pub-network': 'certa',
            'ssl_key_cinderhost1-pub-network': 'keya',
            'ssl_cert_cinderhost1-adm-network': 'certa',
            'ssl_key_cinderhost1-adm-network': 'keya',
        },
    }
}

QUANTUM_NETWORK_SERVICE_RELATION = {
    'quantum-network-service:0': {
        'unit/0': {
            'keystone_host': '10.5.0.1',
            'service_port': '5000',
            'auth_port': '20000',
            'service_tenant': 'tenant',
            'service_username': 'username',
            'service_password': 'password',
            'quantum_host': '10.5.0.2',
            'quantum_port': '9696',
            'quantum_url': 'http://10.5.0.2:9696/v2',
            'region': 'aregion'
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

NOVA_SUB_CONFIG1 = """
nova:
    /etc/nova/nova.conf:
        sections:
            DEFAULT:
                - [nova-key1, value1]
                - [nova-key2, value2]
"""


NOVA_SUB_CONFIG2 = """
nova-compute:
    /etc/nova/nova.conf:
        sections:
            DEFAULT:
                - [nova-key3, value3]
                - [nova-key4, value4]
"""

CINDER_SUB_CONFIG1 = """
cinder:
    /etc/cinder/cinder.conf:
        sections:
            cinder-1-section:
                - [key1, value1]
"""

CINDER_SUB_CONFIG2 = """
cinder:
    /etc/cinder/cinder.conf:
        sections:
            cinder-2-section:
                - [key2, value2]
        not-a-section:
            1234
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
    },
    'cinder-subordinate:0': {
        'cinder-subordinate/0': {
            'private-address': 'cinder_node1',
            'subordinate_configuration': json.dumps(yaml.load(CINDER_SUB_CONFIG1)),
        },
    },
    'cinder-subordinate:1': {
        'cinder-subordinate/1': {
            'private-address': 'cinder_node1',
            'subordinate_configuration': json.dumps(yaml.load(CINDER_SUB_CONFIG2)),
        },
    },
}

SUB_CONFIG_RELATION2 = {
    'nova-ceilometer:6': {
        'ceilometer-agent/0': {
            'private-address': 'nova_node1',
            'subordinate_configuration': json.dumps(yaml.load(NOVA_SUB_CONFIG1)),
        },
    },
    'neutron-plugin:3': {
        'neutron-ovs-plugin/0': {
            'private-address': 'nova_node1',
            'subordinate_configuration': json.dumps(yaml.load(NOVA_SUB_CONFIG2)),
        },
    }
}

NONET_CONFIG = {
    'vip': 'cinderhost1vip',
    'os-internal-network': None,
    'os-admin-network': None,
    'os-public-network': None
}

FULLNET_CONFIG = {
    'vip': '10.5.1.1 10.5.2.1 10.5.3.1',
    'os-internal-network': "10.5.1.0/24",
    'os-admin-network': "10.5.2.0/24",
    'os-public-network': "10.5.3.0/24"
}

MACHINE_MACS = {
    'eth0': 'fe:c5:ce:8e:2b:00',
    'eth1': 'fe:c5:ce:8e:2b:01',
    'eth2': 'fe:c5:ce:8e:2b:02',
    'eth3': 'fe:c5:ce:8e:2b:03',
}

MACHINE_NICS = {
    'eth0': ['192.168.0.1'],
    'eth1': ['192.168.0.2'],
    'eth2': [],
    'eth3': [],
}

ABSENT_MACS = "aa:a5:ae:ae:ab:a4 "

# Imported in contexts.py and needs patching in setUp()
TO_PATCH = [
    'b64decode',
    'check_call',
    'get_cert',
    'get_ca_cert',
    'install_ca_cert',
    'log',
    'config',
    'relation_get',
    'relation_ids',
    'related_units',
    'is_relation_made',
    'relation_set',
    'unit_get',
    'https',
    'determine_api_port',
    'determine_apache_port',
    'config',
    'is_clustered',
    'time',
    'https',
    'get_address_in_network',
    'get_netmask_for_address',
    'local_unit',
    'get_ipv6_addr',
    'format_ipv6_addr',
    'mkdir',
    'write_file',
    'get_host_ip',
    'charm_name',
    'sysctl_create',
]


class fake_config(object):

    def __init__(self, data):
        self.data = data

    def __call__(self, attr):
        if attr in self.data:
            return self.data[attr]
        return None


class fake_is_relation_made():
    def __init__(self, relations):
        self.relations = relations

    def rel_made(self, relation):
        return self.relations[relation]


class ContextTests(unittest.TestCase):

    def setUp(self):
        for m in TO_PATCH:
            setattr(self, m, self._patch(m))
        # mock at least a single relation + unit
        self.relation_ids.return_value = ['foo:0']
        self.related_units.return_value = ['foo/0']
        self.local_unit.return_value = 'localunit'
        self.format_ipv6_addr.return_value = None
        self.get_host_ip.side_effect = lambda hostname: hostname

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
        self.get_address_in_network.return_value = ''
        self.config.side_effect = fake_config(SHARED_DB_CONFIG)
        shared_db = context.SharedDBContext()
        result = shared_db()
        expected = {
            'database_host': 'dbserver.local',
            'database': 'foodb',
            'database_user': 'adam',
            'database_password': 'foo',
            'database_type': 'mysql',
        }
        self.assertEquals(result, expected)

    def test_shared_db_context_with_data_and_access_net_mismatch(self):
        '''Mismatch between hostname and hostname for access net - defers execution'''
        relation = FakeRelation(
            relation_data=SHARED_DB_RELATION_ACCESS_NETWORK)
        self.relation_get.side_effect = relation.get
        self.get_address_in_network.return_value = '10.5.5.1'
        self.config.side_effect = fake_config(SHARED_DB_CONFIG)
        shared_db = context.SharedDBContext()
        result = shared_db()
        self.assertEquals(result, None)
        self.relation_set.assert_called_with(
            relation_settings={
                'hostname': '10.5.5.1'})

    def test_shared_db_context_with_data_and_access_net_match(self):
        '''Correctly set hostname for access net returns complete context'''
        relation = FakeRelation(
            relation_data=SHARED_DB_RELATION_ACCESS_NETWORK)
        self.relation_get.side_effect = relation.get
        self.get_address_in_network.return_value = 'bar'
        self.config.side_effect = fake_config(SHARED_DB_CONFIG)
        shared_db = context.SharedDBContext()
        result = shared_db()
        expected = {
            'database_host': 'dbserver.local',
            'database': 'foodb',
            'database_user': 'adam',
            'database_password': 'foo',
            'database_type': 'mysql',
        }
        self.assertEquals(result, expected)

    @patch('os.path.exists')
    @patch(open_builtin)
    def test_db_ssl(self, _open, osexists):
        osexists.return_value = False
        ssl_dir = '/etc/dbssl'
        db_ssl_ctxt = context.db_ssl(SHARED_DB_RELATION_SSL, {}, ssl_dir)
        expected = {
            'database_ssl_ca': ssl_dir + '/db-client.ca',
            'database_ssl_cert': ssl_dir + '/db-client.cert',
            'database_ssl_key': ssl_dir + '/db-client.key',
        }
        files = [
            call(expected['database_ssl_ca'], 'w'),
            call(expected['database_ssl_cert'], 'w'),
            call(expected['database_ssl_key'], 'w')
        ]
        for f in files:
            self.assertIn(f, _open.call_args_list)
        self.assertEquals(db_ssl_ctxt, expected)
        decode = [
            call(SHARED_DB_RELATION_SSL['ssl_ca']),
            call(SHARED_DB_RELATION_SSL['ssl_cert']),
            call(SHARED_DB_RELATION_SSL['ssl_key'])
        ]
        self.assertEquals(decode, self.b64decode.call_args_list)

    def test_db_ssl_nossldir(self):
        db_ssl_ctxt = context.db_ssl(SHARED_DB_RELATION_SSL, {}, None)
        self.assertEquals(db_ssl_ctxt, {})

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
        relation = FakeRelation(relation_data=SHARED_DB_RELATION_NAMESPACED)
        self.relation_get.side_effect = relation.get
        result = shared_db()
        self.assertIn(
            call(rid='foo:0', unit='foo/0'),
            self.relation_get.call_args_list)
        self.assertEquals(
            result, {'database': 'quantum',
                     'database_user': 'quantum',
                     'database_password': 'bar2',
                     'database_host': 'bar',
                     'database_type': 'mysql'})

    def test_shared_db_context_with_ipv6(self):
        '''Test shared-db context with ipv6'''
        shared_db = context.SharedDBContext(
            database='quantum', user='quantum', relation_prefix='quantum')
        relation = FakeRelation(relation_data=SHARED_DB_RELATION_NAMESPACED)
        self.relation_get.side_effect = relation.get
        self.format_ipv6_addr.return_value = '[2001:db8:1::1]'
        result = shared_db()
        self.assertIn(
            call(rid='foo:0', unit='foo/0'),
            self.relation_get.call_args_list)
        self.assertEquals(
            result, {'database': 'quantum',
                     'database_user': 'quantum',
                     'database_password': 'bar2',
                     'database_host': '[2001:db8:1::1]',
                     'database_type': 'mysql'})

    def test_postgresql_db_context_with_data(self):
        '''Test postgresql-db context with all required data'''
        relation = FakeRelation(relation_data=POSTGRESQL_DB_RELATION)
        self.relation_get.side_effect = relation.get
        self.config.side_effect = fake_config(POSTGRESQL_DB_CONFIG)
        postgresql_db = context.PostgresqlDBContext()
        result = postgresql_db()
        expected = {
            'database_host': 'dbserver.local',
            'database': 'foodb',
            'database_user': 'adam',
            'database_password': 'foo',
            'database_type': 'postgresql',
        }
        self.assertEquals(result, expected)

    def test_postgresql_db_context_with_missing_relation(self):
        '''Test postgresql-db context missing relation data'''
        incomplete_relation = copy(POSTGRESQL_DB_RELATION)
        incomplete_relation['password'] = None
        relation = FakeRelation(relation_data=incomplete_relation)
        self.relation_get.side_effect = relation.get
        self.config.return_value = POSTGRESQL_DB_CONFIG
        postgresql_db = context.PostgresqlDBContext()
        result = postgresql_db()
        self.assertEquals(result, {})

    def test_postgresql_db_context_with_missing_config(self):
        '''Test postgresql-db context missing relation data'''
        incomplete_config = copy(POSTGRESQL_DB_CONFIG)
        del incomplete_config['database']
        self.config.side_effect = fake_config(incomplete_config)
        relation = FakeRelation(relation_data=POSTGRESQL_DB_RELATION)
        self.relation_get.side_effect = relation.get
        self.config.return_value = incomplete_config
        postgresql_db = context.PostgresqlDBContext()
        self.assertRaises(context.OSContextError, postgresql_db)

    def test_postgresql_db_context_with_params(self):
        '''Test postgresql-db context with object parameters'''
        postgresql_db = context.PostgresqlDBContext(database='quantum')
        result = postgresql_db()
        self.assertEquals(result['database'], 'quantum')

    def test_identity_service_context_with_data(self):
        '''Test shared-db context with all required data'''
        relation = FakeRelation(relation_data=IDENTITY_SERVICE_RELATION_UNSET)
        self.relation_get.side_effect = relation.get
        identity_service = context.IdentityServiceContext()
        result = identity_service()
        expected = {
            'admin_password': 'foo',
            'admin_tenant_name': 'admin',
            'admin_tenant_id': None,
            'admin_user': 'adam',
            'auth_host': 'keystone-host.local',
            'auth_port': '35357',
            'auth_protocol': 'http',
            'service_host': 'keystonehost.local',
            'service_port': '5000',
            'service_protocol': 'http'
        }
        self.assertEquals(result, expected)

    def test_identity_service_context_with_altname(self):
        '''Test identity context when using an explicit relation name'''
        relation = FakeRelation(
            relation_data=APIIDENTITY_SERVICE_RELATION_UNSET
        )
        self.relation_get.side_effect = relation.get
        self.relation_ids.return_value = ['neutron-plugin-api:0']
        self.related_units.return_value = ['neutron-api/0']
        identity_service = context.IdentityServiceContext(
            rel_name='neutron-plugin-api'
        )
        result = identity_service()
        expected = {
            'admin_password': 'foo',
            'admin_tenant_name': 'admin',
            'admin_tenant_id': None,
            'admin_user': 'adam',
            'auth_host': 'keystone-host.local',
            'auth_port': '35357',
            'auth_protocol': 'http',
            'service_host': 'keystonehost.local',
            'service_port': '5000',
            'service_protocol': 'http'
        }
        self.assertEquals(result, expected)

    def test_identity_service_context_with_cache(self):
        '''Test shared-db context with signing cache info'''
        relation = FakeRelation(relation_data=IDENTITY_SERVICE_RELATION_UNSET)
        self.relation_get.side_effect = relation.get
        svc = 'cinder'
        identity_service = context.IdentityServiceContext(service=svc,
                                                          service_user=svc)
        result = identity_service()
        expected = {
            'admin_password': 'foo',
            'admin_tenant_name': 'admin',
            'admin_tenant_id': None,
            'admin_user': 'adam',
            'auth_host': 'keystone-host.local',
            'auth_port': '35357',
            'auth_protocol': 'http',
            'service_host': 'keystonehost.local',
            'service_port': '5000',
            'service_protocol': 'http',
            'signing_dir': '/var/cache/cinder',
        }
        self.assertTrue(self.mkdir.called)
        self.assertEquals(result, expected)

    def test_identity_service_context_with_data_http(self):
        '''Test shared-db context with all required data'''
        relation = FakeRelation(relation_data=IDENTITY_SERVICE_RELATION_HTTP)
        self.relation_get.side_effect = relation.get
        identity_service = context.IdentityServiceContext()
        result = identity_service()
        expected = {
            'admin_password': 'foo',
            'admin_tenant_name': 'admin',
            'admin_tenant_id': '123456',
            'admin_user': 'adam',
            'auth_host': 'keystone-host.local',
            'auth_port': '35357',
            'auth_protocol': 'http',
            'service_host': 'keystonehost.local',
            'service_port': '5000',
            'service_protocol': 'http'
        }
        self.assertEquals(result, expected)

    def test_identity_service_context_with_data_https(self):
        '''Test shared-db context with all required data'''
        relation = FakeRelation(relation_data=IDENTITY_SERVICE_RELATION_HTTPS)
        self.relation_get.side_effect = relation.get
        identity_service = context.IdentityServiceContext()
        result = identity_service()
        expected = {
            'admin_password': 'foo',
            'admin_tenant_name': 'admin',
            'admin_tenant_id': None,
            'admin_user': 'adam',
            'auth_host': 'keystone-host.local',
            'auth_port': '35357',
            'auth_protocol': 'https',
            'service_host': 'keystonehost.local',
            'service_port': '5000',
            'service_protocol': 'https'
        }
        self.assertEquals(result, expected)

    def test_identity_service_context_with_ipv6(self):
        '''Test identity-service context with ipv6'''
        relation = FakeRelation(relation_data=IDENTITY_SERVICE_RELATION_HTTP)
        self.relation_get.side_effect = relation.get
        self.format_ipv6_addr.return_value = '[2001:db8:1::1]'
        identity_service = context.IdentityServiceContext()
        result = identity_service()
        expected = {
            'admin_password': 'foo',
            'admin_tenant_name': 'admin',
            'admin_tenant_id': '123456',
            'admin_user': 'adam',
            'auth_host': '[2001:db8:1::1]',
            'auth_port': '35357',
            'auth_protocol': 'http',
            'service_host': '[2001:db8:1::1]',
            'service_port': '5000',
            'service_protocol': 'http'
        }
        self.assertEquals(result, expected)

    def test_identity_service_context_with_missing_relation(self):
        '''Test shared-db context missing relation data'''
        incomplete_relation = copy(IDENTITY_SERVICE_RELATION_UNSET)
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

    def test_amqp_context_with_data_altname(self):
        '''Test amqp context with alternative relation name'''
        relation = FakeRelation(relation_data=AMQP_RELATION)
        self.relation_get.side_effect = relation.get
        self.config.return_value = AMQP_NOVA_CONFIG
        amqp = context.AMQPContext(
            rel_name='amqp-nova',
            relation_prefix='nova')
        result = amqp()
        expected = {
            'rabbitmq_host': 'rabbithost',
            'rabbitmq_password': 'foobar',
            'rabbitmq_user': 'adam',
            'rabbitmq_virtual_host': 'foo'
        }
        self.assertEquals(result, expected)

    @patch(open_builtin)
    def test_amqp_context_with_data_ssl(self, _open):
        '''Test amqp context with all required data and ssl'''
        relation = FakeRelation(relation_data=AMQP_RELATION_WITH_SSL)
        self.relation_get.side_effect = relation.get
        self.config.return_value = AMQP_CONFIG
        ssl_dir = '/etc/sslamqp'
        amqp = context.AMQPContext(ssl_dir=ssl_dir)
        result = amqp()
        expected = {
            'rabbitmq_host': 'rabbithost',
            'rabbitmq_password': 'foobar',
            'rabbitmq_user': 'adam',
            'rabbit_ssl_port': 5671,
            'rabbitmq_virtual_host': 'foo',
            'rabbit_ssl_ca': ssl_dir + '/rabbit-client-ca.pem',
            'rabbitmq_ha_queues': True,
        }
        _open.assert_called_once_with(ssl_dir + '/rabbit-client-ca.pem', 'w')
        self.assertEquals(result, expected)
        self.assertEquals([call(AMQP_RELATION_WITH_SSL['ssl_ca'])],
                          self.b64decode.call_args_list)

    def test_amqp_context_with_data_ssl_noca(self):
        '''Test amqp context with all required data with ssl but missing ca'''
        relation = FakeRelation(relation_data=AMQP_RELATION_WITH_SSL)
        self.relation_get.side_effect = relation.get
        self.config.return_value = AMQP_CONFIG
        amqp = context.AMQPContext()
        result = amqp()
        expected = {
            'rabbitmq_host': 'rabbithost',
            'rabbitmq_password': 'foobar',
            'rabbitmq_user': 'adam',
            'rabbit_ssl_port': 5671,
            'rabbitmq_virtual_host': 'foo',
            'rabbit_ssl_ca': 'cert',
            'rabbitmq_ha_queues': True,
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
            'rabbitmq_hosts': 'rabbithost1,rabbithost2',
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

    def test_amqp_context_with_ipv6(self):
        '''Test amqp context with ipv6'''
        relation_data = copy(AMQP_AA_RELATION)
        relation = FakeRelation(relation_data=relation_data)
        self.relation_get.side_effect = relation.get
        self.relation_ids.side_effect = relation.relation_ids
        self.related_units.side_effect = relation.relation_units
        self.format_ipv6_addr.return_value = '[2001:db8:1::1]'
        self.config.return_value = AMQP_CONFIG
        amqp = context.AMQPContext()
        result = amqp()
        expected = {
            'rabbitmq_host': '[2001:db8:1::1]',
            'rabbitmq_password': 'foobar',
            'rabbitmq_user': 'adam',
            'rabbitmq_virtual_host': 'foo',
            'rabbitmq_hosts': '[2001:db8:1::1],[2001:db8:1::1]',
        }
        self.assertEquals(result, expected)

    def test_amqp_context_with_oslo_messaging(self):
        """Test amqp context with oslo-messaging-flags option"""
        relation = FakeRelation(relation_data=AMQP_RELATION)
        self.relation_get.side_effect = relation.get
        AMQP_OSLO_CONFIG.update(AMQP_CONFIG)
        self.config.return_value = AMQP_OSLO_CONFIG
        amqp = context.AMQPContext()
        result = amqp()
        expected = {
            'rabbitmq_host': 'rabbithost',
            'rabbitmq_password': 'foobar',
            'rabbitmq_user': 'adam',
            'rabbitmq_virtual_host': 'foo',
            'oslo_messaging_flags': {
                'rabbit_max_retries': '1',
                'rabbit_retry_backoff': '1',
                'rabbit_retry_interval': '1'
            },
        }

        self.assertEquals(result, expected)

    def test_libvirt_config_flags(self):
        self.config.side_effect = fake_config({
            'libvirt-flags': 'iscsi_use_multipath=True,chap_auth=False',
        })

        results = context.LibvirtConfigFlagsContext()()
        self.assertEquals(results, {
            'libvirt_flags': {
                'chap_auth': 'False',
                'iscsi_use_multipath': 'True'
            }
        })

    def test_ceph_no_relids(self):
        '''Test empty ceph realtion'''
        relation = FakeRelation(relation_data={})
        self.relation_ids.side_effect = relation.get
        ceph = context.CephContext()
        result = ceph()
        self.assertEquals(result, {})

    @patch.object(context, 'config')
    @patch('os.path.isdir')
    @patch('os.mkdir')
    @patch.object(context, 'ensure_packages')
    def test_ceph_context_with_data(self, ensure_packages, mkdir, isdir,
                                    mock_config):
        '''Test ceph context with all relation data'''
        config_dict = {'use-syslog': True}

        def fake_config(key):
            return config_dict.get(key)

        mock_config.side_effect = fake_config
        isdir.return_value = False
        relation = FakeRelation(relation_data=CEPH_RELATION)
        self.relation_get.side_effect = relation.get
        self.relation_ids.side_effect = relation.relation_ids
        self.related_units.side_effect = relation.relation_units
        ceph = context.CephContext()
        result = ceph()
        expected = {
            'mon_hosts': 'ceph_node1 ceph_node2',
            'auth': 'foo',
            'key': 'bar',
            'use_syslog': 'true'
        }
        self.assertEquals(result, expected)
        ensure_packages.assert_called_with(['ceph-common'])
        mkdir.assert_called_with('/etc/ceph')

    @patch('os.mkdir')
    @patch.object(context, 'ensure_packages')
    def test_ceph_context_with_missing_data(self, ensure_packages, mkdir):
        '''Test ceph context with missing relation data'''
        relation = deepcopy(CEPH_RELATION)
        for k, v in six.iteritems(relation):
            for u in six.iterkeys(v):
                del relation[k][u]['auth']
        relation = FakeRelation(relation_data=relation)
        self.relation_get.side_effect = relation.get
        self.relation_ids.side_effect = relation.relation_ids
        self.related_units.side_effect = relation.relation_units
        ceph = context.CephContext()
        result = ceph()
        self.assertEquals(result, {})
        self.assertFalse(ensure_packages.called)

    @patch.object(context, 'config')
    @patch('os.path.isdir')
    @patch('os.mkdir')
    @patch.object(context, 'ensure_packages')
    def test_ceph_context_partial_missing_data(self, ensure_packages, mkdir,
                                               isdir, config):
        '''Test ceph context last unit missing data

           Tests a fix to a previously bug which meant only the config from
           last unit was returned so if a valid value was supplied from an
           earlier unit it would be ignored'''
        config.side_effect = fake_config({'use-syslog': 'True'})
        relation = deepcopy(CEPH_RELATION)
        for k, v in six.iteritems(relation):
            last_unit = sorted(six.iterkeys(v))[-1]
            unit_data = relation[k][last_unit]
            del unit_data['auth']
            relation[k][last_unit] = unit_data
        relation = FakeRelation(relation_data=relation)
        self.relation_get.side_effect = relation.get
        self.relation_ids.side_effect = relation.relation_ids
        self.related_units.side_effect = relation.relation_units
        ceph = context.CephContext()
        result = ceph()
        expected = {
            'mon_hosts': 'ceph_node1 ceph_node2',
            'auth': 'foo',
            'key': 'bar',
            'use_syslog': 'true'
        }
        self.assertEquals(result, expected)

    @patch.object(context, 'config')
    @patch('os.path.isdir')
    @patch('os.mkdir')
    @patch.object(context, 'ensure_packages')
    def test_ceph_context_with_public_addr(
            self, ensure_packages, mkdir, isdir, mock_config):
        '''Test ceph context in host with multiple networks with all
        relation data'''
        isdir.return_value = False
        config_dict = {'use-syslog': True}

        def fake_config(key):
            return config_dict.get(key)

        mock_config.side_effect = fake_config
        relation = FakeRelation(relation_data=CEPH_RELATION_WITH_PUBLIC_ADDR)
        self.relation_get.side_effect = relation.get
        self.relation_ids.side_effect = relation.relation_ids
        self.related_units.side_effect = relation.relation_units
        ceph = context.CephContext()
        result = ceph()
        expected = {
            'mon_hosts': '192.168.1.10 192.168.1.11',
            'auth': 'foo',
            'key': 'bar',
            'use_syslog': 'true',
        }
        self.assertEquals(result, expected)
        ensure_packages.assert_called_with(['ceph-common'])
        mkdir.assert_called_with('/etc/ceph')

    @patch.object(context, 'config')
    @patch('os.path.isdir')
    @patch('os.mkdir')
    @patch.object(context, 'ensure_packages')
    def test_ceph_context_with_rbd_cache(self, ensure_packages, mkdir, isdir,
                                         mock_config):
        isdir.return_value = False
        config_dict = {'rbd-client-cache': 'enabled',
                       'use-syslog': False}

        def fake_config(key):
            return config_dict.get(key)

        mock_config.side_effect = fake_config
        relation = FakeRelation(relation_data=CEPH_RELATION_WITH_PUBLIC_ADDR)
        self.relation_get.side_effect = relation.get
        self.relation_ids.side_effect = relation.relation_ids
        self.related_units.side_effect = relation.relation_units

        class CephContextWithRBDCache(context.CephContext):
            def __call__(self):
                ctxt = super(CephContextWithRBDCache, self).__call__()

                rbd_cache = fake_config('rbd-client-cache') or ""
                if rbd_cache.lower() == "enabled":
                    ctxt['rbd_client_cache_settings'] = \
                        {'rbd cache': 'true',
                         'rbd cache writethrough until flush': 'true'}
                elif rbd_cache.lower() == "disabled":
                    ctxt['rbd_client_cache_settings'] = \
                        {'rbd cache': 'false'}

                return ctxt

        ceph = CephContextWithRBDCache()
        result = ceph()
        expected = {
            'mon_hosts': '192.168.1.10 192.168.1.11',
            'auth': 'foo',
            'key': 'bar',
            'use_syslog': 'false',
        }
        expected['rbd_client_cache_settings'] = \
            {'rbd cache': 'true',
             'rbd cache writethrough until flush': 'true'}

        self.assertDictEqual(result, expected)
        ensure_packages.assert_called_with(['ceph-common'])
        mkdir.assert_called_with('/etc/ceph')

    @patch.object(context, 'config')
    def test_sysctl_context_with_config(self, config):
        self.charm_name.return_value = 'test-charm'
        config.return_value = '{ kernel.max_pid: "1337"}'
        self.sysctl_create.return_value = True
        ctxt = context.SysctlContext()
        result = ctxt()
        self.sysctl_create.assert_called_with(
            config.return_value,
            "/etc/sysctl.d/50-test-charm.conf")

        self.assertTrue(result, {'sysctl': config.return_value})

    @patch.object(context, 'config')
    def test_sysctl_context_without_config(self, config):
        self.charm_name.return_value = 'test-charm'
        config.return_value = None
        self.sysctl_create.return_value = True
        ctxt = context.SysctlContext()
        result = ctxt()
        self.assertTrue(self.sysctl_create.called == 0)
        self.assertTrue(result, {'sysctl': config.return_value})

    @patch.object(context, 'config')
    @patch('os.path.isdir')
    @patch('os.mkdir')
    @patch.object(context, 'ensure_packages')
    def test_ceph_context_missing_public_addr(
            self, ensure_packages, mkdir, isdir, mock_config):
        '''Test ceph context in host with multiple networks with no
        ceph-public-addr in relation data'''
        isdir.return_value = False
        config_dict = {'use-syslog': True}

        def fake_config(key):
            return config_dict.get(key)

        mock_config.side_effect = fake_config
        relation = deepcopy(CEPH_RELATION_WITH_PUBLIC_ADDR)
        del relation['ceph:0']['ceph/0']['ceph-public-address']
        relation = FakeRelation(relation_data=relation)
        self.relation_get.side_effect = relation.get
        self.relation_ids.side_effect = relation.relation_ids
        self.related_units.side_effect = relation.relation_units
        ceph = context.CephContext()

        result = ceph()
        expected = {
            'mon_hosts': '192.168.1.11 ceph_node1',
            'auth': 'foo',
            'key': 'bar',
            'use_syslog': 'true',
        }
        self.assertEquals(result, expected)
        ensure_packages.assert_called_with(['ceph-common'])
        mkdir.assert_called_with('/etc/ceph')

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
        self.get_address_in_network.return_value = None
        self.get_netmask_for_address.return_value = '255.255.0.0'
        self.config.return_value = False
        self.maxDiff = None
        haproxy = context.HAProxyContext()
        with patch_open() as (_open, _file):
            result = haproxy()
        ex = {
            'frontends': {
                'cluster-peer0.localnet': {
                    'network': 'cluster-peer0.localnet/255.255.0.0',
                    'backends': {
                        'peer-0': 'cluster-peer0.localnet',
                        'peer-1': 'cluster-peer1.localnet',
                        'peer-2': 'cluster-peer2.localnet',
                    }
                }
            },
            'default_backend': 'cluster-peer0.localnet',
            'local_host': '127.0.0.1',
            'haproxy_host': '0.0.0.0',
            'stat_port': ':8888',
        }
        # the context gets generated.
        self.assertEquals(ex, result)
        # and /etc/default/haproxy is updated.
        self.assertEquals(_file.write.call_args_list,
                          [call('ENABLED=1\n')])

    @patch('charmhelpers.contrib.openstack.context.unit_get')
    @patch('charmhelpers.contrib.openstack.context.local_unit')
    def test_haproxy_context_with_data_timeout(self, local_unit, unit_get):
        '''Test haproxy context with all relation data and timeout'''
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
        self.get_address_in_network.return_value = None
        self.get_netmask_for_address.return_value = '255.255.0.0'
        self.config.return_value = False
        self.maxDiff = None
        c = fake_config(HAPROXY_CONFIG)
        c.data['prefer-ipv6'] = False
        self.config.side_effect = c
        haproxy = context.HAProxyContext()
        with patch_open() as (_open, _file):
            result = haproxy()
        ex = {
            'frontends': {
                'cluster-peer0.localnet': {
                    'network': 'cluster-peer0.localnet/255.255.0.0',
                    'backends': {
                        'peer-0': 'cluster-peer0.localnet',
                        'peer-1': 'cluster-peer1.localnet',
                        'peer-2': 'cluster-peer2.localnet',
                    }
                }
            },
            'default_backend': 'cluster-peer0.localnet',
            'local_host': '127.0.0.1',
            'haproxy_host': '0.0.0.0',
            'stat_port': ':8888',
            'haproxy_client_timeout': 50000,
            'haproxy_server_timeout': 50000,
        }
        # the context gets generated.
        self.assertEquals(ex, result)
        # and /etc/default/haproxy is updated.
        self.assertEquals(_file.write.call_args_list,
                          [call('ENABLED=1\n')])

    @patch('charmhelpers.contrib.openstack.context.unit_get')
    @patch('charmhelpers.contrib.openstack.context.local_unit')
    def test_haproxy_context_with_data_multinet(self, local_unit, unit_get):
        '''Test haproxy context with all relation data for network splits'''
        cluster_relation = {
            'cluster:0': {
                'peer/1': {
                    'private-address': 'cluster-peer1.localnet',
                    'admin-address': 'cluster-peer1.admin',
                    'internal-address': 'cluster-peer1.internal',
                    'public-address': 'cluster-peer1.public',
                },
                'peer/2': {
                    'private-address': 'cluster-peer2.localnet',
                    'admin-address': 'cluster-peer2.admin',
                    'internal-address': 'cluster-peer2.internal',
                    'public-address': 'cluster-peer2.public',
                },
            },
        }
        local_unit.return_value = 'peer/0'
        unit_get.return_value = 'cluster-peer0.localnet'
        relation = FakeRelation(cluster_relation)
        self.relation_ids.side_effect = relation.relation_ids
        self.relation_get.side_effect = relation.get
        self.related_units.side_effect = relation.relation_units
        self.get_address_in_network.side_effect = [
            'cluster-peer0.admin',
            'cluster-peer0.internal',
            'cluster-peer0.public'
        ]
        self.get_netmask_for_address.return_value = '255.255.0.0'
        self.config.return_value = False
        self.maxDiff = None
        haproxy = context.HAProxyContext()
        with patch_open() as (_open, _file):
            result = haproxy()
        ex = {
            'frontends': {
                'cluster-peer0.admin': {
                    'network': 'cluster-peer0.admin/255.255.0.0',
                    'backends': {
                        'peer-0': 'cluster-peer0.admin',
                        'peer-1': 'cluster-peer1.admin',
                        'peer-2': 'cluster-peer2.admin',
                    }
                },
                'cluster-peer0.internal': {
                    'network': 'cluster-peer0.internal/255.255.0.0',
                    'backends': {
                        'peer-0': 'cluster-peer0.internal',
                        'peer-1': 'cluster-peer1.internal',
                        'peer-2': 'cluster-peer2.internal',
                    }
                },
                'cluster-peer0.public': {
                    'network': 'cluster-peer0.public/255.255.0.0',
                    'backends': {
                        'peer-0': 'cluster-peer0.public',
                        'peer-1': 'cluster-peer1.public',
                        'peer-2': 'cluster-peer2.public',
                    }
                },
                'cluster-peer0.localnet': {
                    'network': 'cluster-peer0.localnet/255.255.0.0',
                    'backends': {
                        'peer-0': 'cluster-peer0.localnet',
                        'peer-1': 'cluster-peer1.localnet',
                        'peer-2': 'cluster-peer2.localnet',
                    }
                }
            },
            'default_backend': 'cluster-peer0.localnet',
            'local_host': '127.0.0.1',
            'haproxy_host': '0.0.0.0',
            'stat_port': ':8888',
        }
        # the context gets generated.
        self.assertEquals(ex, result)
        # and /etc/default/haproxy is updated.
        self.assertEquals(_file.write.call_args_list,
                          [call('ENABLED=1\n')])

    @patch('charmhelpers.contrib.openstack.context.unit_get')
    @patch('charmhelpers.contrib.openstack.context.local_unit')
    def test_haproxy_context_with_data_ipv6(
            self, local_unit, unit_get):
        '''Test haproxy context with all relation data ipv6'''
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
        relation = FakeRelation(cluster_relation)
        self.relation_ids.side_effect = relation.relation_ids
        self.relation_get.side_effect = relation.get
        self.related_units.side_effect = relation.relation_units
        self.get_address_in_network.return_value = None
        self.get_netmask_for_address.return_value = \
            'FFFF:FFFF:FFFF:FFFF:0000:0000:0000:0000'
        self.get_ipv6_addr.return_value = ['cluster-peer0.localnet']
        c = fake_config(HAPROXY_CONFIG)
        c.data['prefer-ipv6'] = True
        self.config.side_effect = c
        self.maxDiff = None
        haproxy = context.HAProxyContext()
        with patch_open() as (_open, _file):
            result = haproxy()
        ex = {
            'frontends': {
                'cluster-peer0.localnet': {
                    'network': 'cluster-peer0.localnet/'
                    'FFFF:FFFF:FFFF:FFFF:0000:0000:0000:0000',
                    'backends': {
                        'peer-0': 'cluster-peer0.localnet',
                        'peer-1': 'cluster-peer1.localnet',
                        'peer-2': 'cluster-peer2.localnet',
                    }
                }
            },
            'default_backend': 'cluster-peer0.localnet',
            'local_host': 'ip6-localhost',
            'haproxy_server_timeout': 50000,
            'haproxy_client_timeout': 50000,
            'haproxy_host': '::',
            'stat_port': ':::8888',
            'ipv6': True
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
        self.config.return_value = False
        haproxy = context.HAProxyContext()
        self.assertEquals({}, haproxy())

    @patch('charmhelpers.contrib.openstack.context.unit_get')
    @patch('charmhelpers.contrib.openstack.context.local_unit')
    def test_haproxy_context_with_no_peers_singlemode(self, local_unit, unit_get):
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
        self.config.return_value = False
        self.get_address_in_network.return_value = None
        self.get_netmask_for_address.return_value = '255.255.0.0'
        with patch_open() as (_open, _file):
            result = context.HAProxyContext(singlenode_mode=True)()
        ex = {
            'frontends': {
                'lonely.clusterpeer.howsad': {
                    'backends': {
                        'peer-0': 'lonely.clusterpeer.howsad'
                    },
                    'network': 'lonely.clusterpeer.howsad/255.255.0.0'
                },
            },
            'default_backend': 'lonely.clusterpeer.howsad',
            'haproxy_host': '0.0.0.0',
            'local_host': '127.0.0.1',
            'stat_port': ':8888'
        }
        self.assertEquals(ex, result)
        # and /etc/default/haproxy is updated.
        self.assertEquals(_file.write.call_args_list,
                          [call('ENABLED=1\n')])

    def test_https_context_with_no_https(self):
        '''Test apache2 https when no https data available'''
        apache = context.ApacheSSLContext()
        self.https.return_value = False
        self.assertEquals({}, apache())

    @patch('charmhelpers.contrib.network.ip.is_address_in_network')
    def _test_https_context(self, mock_is_address_in_network, apache,
                            is_clustered, peer_units,
                            network_config=NONET_CONFIG, multinet=False,
                            cn_provided=True):
        self.https.return_value = True
        vips = network_config['vip'].split()
        if multinet:
            self.get_address_in_network.side_effect = ['10.5.1.100',
                                                       '10.5.2.100',
                                                       '10.5.3.100']
        else:
            self.get_address_in_network.return_value = 'cinderhost1'

        config = {}
        config.update(network_config)
        self.config.side_effect = lambda key: config[key]

        self.unit_get.return_value = 'cinderhost1'
        self.is_clustered.return_value = is_clustered

        apache = context.ApacheSSLContext()
        apache.configure_cert = MagicMock()
        apache.enable_modules = MagicMock()
        apache.configure_ca = MagicMock()
        apache.canonical_names = MagicMock(return_value=[])

        if is_clustered:
            if cn_provided:
                apache.canonical_names.return_value = \
                    network_config['vip'].split()

            self.determine_api_port.return_value = 8756
            self.determine_apache_port.return_value = 8766
            if len(vips) > 1:
                mock_is_address_in_network.side_effect = [
                    True, False, True, False, False, True
                ]
            else:
                mock_is_address_in_network.return_value = True
        else:
            if cn_provided:
                apache.canonical_names.return_value = ['cinderhost1']

            self.determine_api_port.return_value = 8766
            self.determine_apache_port.return_value = 8776

        apache.external_ports = '8776'
        apache.service_namespace = 'cinder'

        if is_clustered:
            if len(vips) > 1:
                ex = {
                    'namespace': 'cinder',
                    'endpoints': [('10.5.1.100', '10.5.1.1', 8766, 8756),
                                  ('10.5.2.100', '10.5.2.1', 8766, 8756),
                                  ('10.5.3.100', '10.5.3.1', 8766, 8756)],
                    'ext_ports': [8766]
                }
            else:
                ex = {
                    'namespace': 'cinder',
                    'endpoints': [('cinderhost1', 'cinderhost1vip',
                                   8766, 8756)],
                    'ext_ports': [8766]
                }
        else:
            if multinet:
                ex = {
                    'namespace': 'cinder',
                    'endpoints': sorted([
                        ('10.5.3.100', '10.5.3.100', 8776, 8766),
                        ('10.5.2.100', '10.5.2.100', 8776, 8766),
                        ('10.5.1.100', '10.5.1.100', 8776, 8766)]),
                    'ext_ports': [8776]
                }
            else:
                ex = {
                    'namespace': 'cinder',
                    'endpoints': [('cinderhost1', 'cinderhost1', 8776, 8766)],
                    'ext_ports': [8776]
                }

        self.assertEquals(ex, apache())
        if is_clustered:
            if len(vips) > 1:
                apache.configure_cert.assert_has_calls([
                    call('10.5.1.1'),
                    call('10.5.2.1'),
                    call('10.5.3.1')
                ])
            else:
                apache.configure_cert.assert_called_with('cinderhost1vip')
        else:
            if cn_provided:
                apache.configure_cert.assert_called_with('cinderhost1')
            else:
                apache.configure_cert.assert_called_with('10.0.0.1')

        self.assertTrue(apache.configure_ca.called)
        self.assertTrue(apache.enable_modules.called)
        self.assertTrue(apache.configure_cert.called)

    @patch.object(context, 'resolve_address')
    def test_https_context_no_cn(self, mock_resolve_address):
        '''Test apache2 https with no cn provided'''
        mock_resolve_address.return_value = "10.0.0.1"
        apache = context.ApacheSSLContext()
        self._test_https_context(apache, is_clustered=False, peer_units=None,
                                 cn_provided=False)

    def test_https_context_no_peers_no_cluster(self):
        '''Test apache2 https on a single, unclustered unit'''
        apache = context.ApacheSSLContext()
        self._test_https_context(apache, is_clustered=False, peer_units=None)

    def test_https_context_multinetwork(self):
        apache = context.ApacheSSLContext()
        self._test_https_context(apache, is_clustered=False, peer_units=None,
                                 network_config=FULLNET_CONFIG, multinet=True)

    def test_https_context_multinetwork_cluster(self):
        apache = context.ApacheSSLContext()
        self._test_https_context(apache, is_clustered=True, peer_units=None,
                                 network_config=FULLNET_CONFIG, multinet=True)

    def test_https_context_wth_peers_no_cluster(self):
        '''Test apache2 https on a unclustered unit with peers'''
        apache = context.ApacheSSLContext()
        self._test_https_context(apache, is_clustered=False, peer_units=[1, 2])

    def test_https_context_wth_peers_cluster(self):
        '''Test apache2 https on a clustered unit with peers'''
        apache = context.ApacheSSLContext()
        self._test_https_context(apache, is_clustered=True, peer_units=[1, 2])

    def test_https_context_loads_correct_apache_mods(self):
        '''Test apache2 context also loads required apache modules'''
        apache = context.ApacheSSLContext()
        apache.enable_modules()
        ex_cmd = ['a2enmod', 'ssl', 'proxy', 'proxy_http']
        self.check_call.assert_called_with(ex_cmd)

    def test_https_configure_cert(self):
        '''Test apache2 properly installs certs and keys to disk'''
        self.get_cert.return_value = ('SSL_CERT', 'SSL_KEY')
        self.b64decode.side_effect = [b'SSL_CERT', b'SSL_KEY']
        apache = context.ApacheSSLContext()
        apache.service_namespace = 'cinder'
        apache.configure_cert('test-cn')
        # appropriate directories are created.
        self.mkdir.assert_called_with(path='/etc/apache2/ssl/cinder')
        # appropriate files are written.
        files = [call(path='/etc/apache2/ssl/cinder/cert_test-cn',
                      content=b'SSL_CERT'),
                 call(path='/etc/apache2/ssl/cinder/key_test-cn',
                      content=b'SSL_KEY')]
        self.write_file.assert_has_calls(files)
        # appropriate bits are b64decoded.
        decode = [call('SSL_CERT'), call('SSL_KEY')]
        self.assertEquals(decode, self.b64decode.call_args_list)

    def test_https_configure_cert_deprecated(self):
        '''Test apache2 properly installs certs and keys to disk'''
        self.get_cert.return_value = ('SSL_CERT', 'SSL_KEY')
        self.b64decode.side_effect = ['SSL_CERT', 'SSL_KEY']
        apache = context.ApacheSSLContext()
        apache.service_namespace = 'cinder'
        apache.configure_cert()
        # appropriate directories are created.
        self.mkdir.assert_called_with(path='/etc/apache2/ssl/cinder')
        # appropriate files are written.
        files = [call(path='/etc/apache2/ssl/cinder/cert',
                      content='SSL_CERT'),
                 call(path='/etc/apache2/ssl/cinder/key',
                      content='SSL_KEY')]
        self.write_file.assert_has_calls(files)
        # appropriate bits are b64decoded.
        decode = [call('SSL_CERT'), call('SSL_KEY')]
        self.assertEquals(decode, self.b64decode.call_args_list)

    def test_https_canonical_names(self):
        rel = FakeRelation(IDENTITY_RELATION_SINGLE_CERT)
        self.relation_ids.side_effect = rel.relation_ids
        self.related_units.side_effect = rel.relation_units
        self.relation_get.side_effect = rel.get
        apache = context.ApacheSSLContext()
        self.assertEquals(apache.canonical_names(), ['cinderhost1'])
        rel.relation_data = IDENTITY_RELATION_MULTIPLE_CERT
        self.assertEquals(apache.canonical_names(),
                          sorted(['cinderhost1-adm-network',
                                  'cinderhost1-int-network',
                                  'cinderhost1-pub-network']))
        rel.relation_data = IDENTITY_RELATION_NO_CERT
        self.assertEquals(apache.canonical_names(), [])

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

    @patch.object(context.NeutronContext, 'neutron_security_groups')
    @patch.object(context, 'unit_private_ip')
    @patch.object(context, 'neutron_plugin_attribute')
    def test_neutron_nvp_plugin_context(self, attr, ip, sec_groups):
        ip.return_value = '10.0.0.1'
        sec_groups.__get__ = MagicMock(return_value=True)
        attr.return_value = 'some.quantum.driver.class'
        neutron = context.NeutronContext()
        self.assertEquals({
            'config': 'some.quantum.driver.class',
            'core_plugin': 'some.quantum.driver.class',
            'neutron_plugin': 'nvp',
            'neutron_security_groups': True,
            'local_ip': '10.0.0.1'}, neutron.nvp_ctxt())

    @patch.object(context, 'config')
    @patch.object(context.NeutronContext, 'neutron_security_groups')
    @patch.object(context, 'unit_private_ip')
    @patch.object(context, 'neutron_plugin_attribute')
    def test_neutron_n1kv_plugin_context(self, attr, ip, sec_groups, config):
        ip.return_value = '10.0.0.1'
        sec_groups.__get__ = MagicMock(return_value=True)
        attr.return_value = 'some.quantum.driver.class'
        config.return_value = 'n1kv'
        neutron = context.NeutronContext()
        self.assertEquals({
            'core_plugin': 'some.quantum.driver.class',
            'neutron_plugin': 'n1kv',
            'neutron_security_groups': True,
            'local_ip': '10.0.0.1',
            'config': 'some.quantum.driver.class',
            'vsm_ip': 'n1kv',
            'vsm_username': 'n1kv',
            'vsm_password': 'n1kv',
            'user_config_flags': {},
            'restrict_policy_profiles': 'n1kv',
        }, neutron.n1kv_ctxt())

    @patch.object(context.NeutronContext, 'neutron_security_groups')
    @patch.object(context, 'unit_private_ip')
    @patch.object(context, 'neutron_plugin_attribute')
    def test_neutron_calico_plugin_context(self, attr, ip, sec_groups):
        ip.return_value = '10.0.0.1'
        sec_groups.__get__ = MagicMock(return_value=True)
        attr.return_value = 'some.quantum.driver.class'
        neutron = context.NeutronContext()
        self.assertEquals({
            'config': 'some.quantum.driver.class',
            'core_plugin': 'some.quantum.driver.class',
            'neutron_plugin': 'Calico',
            'neutron_security_groups': True,
            'local_ip': '10.0.0.1'}, neutron.calico_ctxt())

    @patch.object(context.NeutronContext, 'neutron_security_groups')
    @patch.object(context, 'unit_private_ip')
    @patch.object(context, 'neutron_plugin_attribute')
    def test_neutron_plumgrid_plugin_context(self, attr, ip, sec_groups):
        ip.return_value = '10.0.0.1'
        sec_groups.__get__ = MagicMock(return_value=True)
        attr.return_value = 'some.quantum.driver.class'
        neutron = context.NeutronContext()
        self.assertEquals({
            'config': 'some.quantum.driver.class',
            'core_plugin': 'some.quantum.driver.class',
            'neutron_plugin': 'plumgrid',
            'neutron_security_groups': True,
            'local_ip': '10.0.0.1'}, neutron.pg_ctxt())

    @patch.object(context.NeutronContext, 'neutron_security_groups')
    @patch.object(context, 'unit_private_ip')
    @patch.object(context, 'neutron_plugin_attribute')
    def test_neutron_nuage_plugin_context(self, attr, ip, sec_groups):
        ip.return_value = '10.0.0.1'
        sec_groups.__get__ = MagicMock(return_value=True)
        attr.return_value = 'some.quantum.driver.class'
        neutron = context.NeutronContext()
        self.assertEquals({
            'config': 'some.quantum.driver.class',
            'core_plugin': 'some.quantum.driver.class',
            'neutron_plugin': 'vsp',
            'neutron_security_groups': True,
            'local_ip': '10.0.0.1'}, neutron.nuage_ctxt())

    @patch.object(context.NeutronContext, 'neutron_security_groups')
    @patch.object(context, 'unit_private_ip')
    @patch.object(context, 'neutron_plugin_attribute')
    def test_neutron_midonet_plugin_context(self, attr, ip, sec_groups):
        ip.return_value = '10.0.0.1'
        sec_groups.__get__ = MagicMock(return_value=True)
        attr.return_value = 'some.quantum.driver.class'
        neutron = context.NeutronContext()
        self.assertEquals({
            'config': 'some.quantum.driver.class',
            'core_plugin': 'some.quantum.driver.class',
            'neutron_plugin': 'midonet',
            'neutron_security_groups': True,
            'local_ip': '10.0.0.1'}, neutron.midonet_ctxt())

    @patch('charmhelpers.contrib.openstack.context.unit_get')
    @patch.object(context.NeutronContext, 'network_manager')
    def test_neutron_neutron_ctxt(self, mock_network_manager,
                                  mock_unit_get):
        vip = '88.11.22.33'
        priv_addr = '10.0.0.1'
        mock_unit_get.return_value = priv_addr
        neutron = context.NeutronContext()

        config = {'vip': vip}
        self.config.side_effect = lambda key: config[key]
        mock_network_manager.__get__ = Mock(return_value='neutron')

        self.is_clustered.return_value = False
        self.assertEquals(
            {'network_manager': 'neutron',
             'neutron_url': 'https://%s:9696' % (priv_addr)},
            neutron.neutron_ctxt()
        )

        self.is_clustered.return_value = True
        self.assertEquals(
            {'network_manager': 'neutron',
             'neutron_url': 'https://%s:9696' % (vip)},
            neutron.neutron_ctxt()
        )

    @patch('charmhelpers.contrib.openstack.context.unit_get')
    @patch.object(context.NeutronContext, 'network_manager')
    def test_neutron_neutron_ctxt_http(self, mock_network_manager,
                                       mock_unit_get):
        vip = '88.11.22.33'
        priv_addr = '10.0.0.1'
        mock_unit_get.return_value = priv_addr
        neutron = context.NeutronContext()

        config = {'vip': vip}
        self.config.side_effect = lambda key: config[key]
        self.https.return_value = False
        mock_network_manager.__get__ = Mock(return_value='neutron')

        self.is_clustered.return_value = False
        self.assertEquals(
            {'network_manager': 'neutron',
             'neutron_url': 'http://%s:9696' % (priv_addr)},
            neutron.neutron_ctxt()
        )

        self.is_clustered.return_value = True
        self.assertEquals(
            {'network_manager': 'neutron',
             'neutron_url': 'http://%s:9696' % (vip)},
            neutron.neutron_ctxt()
        )

    @patch.object(context.NeutronContext, 'neutron_ctxt')
    @patch.object(context.NeutronContext, '_save_flag_file')
    @patch.object(context.NeutronContext, 'ovs_ctxt')
    @patch.object(context.NeutronContext, 'plugin')
    @patch.object(context.NeutronContext, '_ensure_packages')
    @patch.object(context.NeutronContext, 'network_manager')
    def test_neutron_main_context_generation(self, mock_network_manager,
                                             mock_ensure_packages,
                                             mock_plugin, mock_ovs_ctxt,
                                             mock_save_flag_file,
                                             mock_neutron_ctxt):

        mock_neutron_ctxt.return_value = {'network_manager': 'neutron',
                                          'neutron_url': 'https://foo:9696'}
        config = {'neutron-alchemy-flags': None}
        self.config.side_effect = lambda key: config[key]
        neutron = context.NeutronContext()

        mock_network_manager.__get__ = Mock(return_value='flatdhcpmanager')
        mock_plugin.__get__ = Mock()

        self.assertEquals({}, neutron())
        self.assertTrue(mock_network_manager.__get__.called)
        self.assertFalse(mock_plugin.__get__.called)

        mock_network_manager.__get__.return_value = 'neutron'
        mock_plugin.__get__ = Mock(return_value=None)
        self.assertEquals({}, neutron())
        self.assertTrue(mock_plugin.__get__.called)

        mock_ovs_ctxt.return_value = {'ovs': 'ovs_context'}
        mock_plugin.__get__.return_value = 'ovs'
        self.assertEquals(
            {'network_manager': 'neutron',
             'ovs': 'ovs_context',
             'neutron_url': 'https://foo:9696'},
            neutron()
        )

    @patch.object(context.NeutronContext, 'neutron_ctxt')
    @patch.object(context.NeutronContext, '_save_flag_file')
    @patch.object(context.NeutronContext, 'nvp_ctxt')
    @patch.object(context.NeutronContext, 'plugin')
    @patch.object(context.NeutronContext, '_ensure_packages')
    @patch.object(context.NeutronContext, 'network_manager')
    def test_neutron_main_context_gen_nvp_and_alchemy(self,
                                                      mock_network_manager,
                                                      mock_ensure_packages,
                                                      mock_plugin,
                                                      mock_nvp_ctxt,
                                                      mock_save_flag_file,
                                                      mock_neutron_ctxt):

        mock_neutron_ctxt.return_value = {'network_manager': 'neutron',
                                          'neutron_url': 'https://foo:9696'}
        config = {'neutron-alchemy-flags': 'pool_size=20'}
        self.config.side_effect = lambda key: config[key]
        neutron = context.NeutronContext()

        mock_network_manager.__get__ = Mock(return_value='flatdhcpmanager')
        mock_plugin.__get__ = Mock()

        self.assertEquals({}, neutron())
        self.assertTrue(mock_network_manager.__get__.called)
        self.assertFalse(mock_plugin.__get__.called)

        mock_network_manager.__get__.return_value = 'neutron'
        mock_plugin.__get__ = Mock(return_value=None)
        self.assertEquals({}, neutron())
        self.assertTrue(mock_plugin.__get__.called)

        mock_nvp_ctxt.return_value = {'nvp': 'nvp_context'}
        mock_plugin.__get__.return_value = 'nvp'
        self.assertEquals(
            {'network_manager': 'neutron',
             'nvp': 'nvp_context',
             'neutron_alchemy_flags': {'pool_size': '20'},
             'neutron_url': 'https://foo:9696'},
            neutron()
        )

    @patch.object(context.NeutronContext, 'neutron_ctxt')
    @patch.object(context.NeutronContext, '_save_flag_file')
    @patch.object(context.NeutronContext, 'calico_ctxt')
    @patch.object(context.NeutronContext, 'plugin')
    @patch.object(context.NeutronContext, '_ensure_packages')
    @patch.object(context.NeutronContext, 'network_manager')
    def test_neutron_main_context_gen_calico(self, mock_network_manager,
                                             mock_ensure_packages,
                                             mock_plugin, mock_ovs_ctxt,
                                             mock_save_flag_file,
                                             mock_neutron_ctxt):

        mock_neutron_ctxt.return_value = {'network_manager': 'neutron',
                                          'neutron_url': 'https://foo:9696'}
        config = {'neutron-alchemy-flags': None}
        self.config.side_effect = lambda key: config[key]
        neutron = context.NeutronContext()

        mock_network_manager.__get__ = Mock(return_value='flatdhcpmanager')
        mock_plugin.__get__ = Mock()

        self.assertEquals({}, neutron())
        self.assertTrue(mock_network_manager.__get__.called)
        self.assertFalse(mock_plugin.__get__.called)

        mock_network_manager.__get__.return_value = 'neutron'
        mock_plugin.__get__ = Mock(return_value=None)
        self.assertEquals({}, neutron())
        self.assertTrue(mock_plugin.__get__.called)

        mock_ovs_ctxt.return_value = {'Calico': 'calico_context'}
        mock_plugin.__get__.return_value = 'Calico'
        self.assertEquals(
            {'network_manager': 'neutron',
             'Calico': 'calico_context',
             'neutron_url': 'https://foo:9696'},
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

    @patch.object(context, 'config')
    def test_os_configflag_context_custom(self, config):
        flags = context.OSConfigFlagContext(
            charm_flag='api-config-flags',
            template_flag='api_config_flags')

        # single
        config.return_value = 'deadbeef=True'
        self.assertEquals({
            'api_config_flags': {
                'deadbeef': 'True',
            }
        }, flags())

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
        cinder_sub_ctxt = context.SubordinateConfigContext(
            service='cinder',
            config_file='/etc/cinder/cinder.conf',
            interface='cinder-subordinate',
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
        self.assertEquals(
            cinder_sub_ctxt(),
            {'sections': {
                'cinder-1-section': [
                    ['key1', 'value1']],
                'cinder-2-section': [
                    ['key2', 'value2']]

            }, 'not-a-section': 1234}
        )

        # subrodinate supplies nothing for given config
        glance_sub_ctxt.config_file = '/etc/glance/glance-api-paste.ini'
        self.assertEquals(glance_sub_ctxt(), {'sections': {}})

        # subordinate supplies bad input
        self.assertEquals(foo_sub_ctxt(), {'sections': {}})

    def test_os_subordinate_config_context_multiple(self):
        relation = FakeRelation(relation_data=SUB_CONFIG_RELATION2)
        self.relation_get.side_effect = relation.get
        self.relation_ids.side_effect = relation.relation_ids
        self.related_units.side_effect = relation.relation_units
        nova_sub_ctxt = context.SubordinateConfigContext(
            service=['nova', 'nova-compute'],
            config_file='/etc/nova/nova.conf',
            interface=['nova-ceilometer', 'neutron-plugin'],
        )
        self.assertEquals(
            nova_sub_ctxt(),
            {'sections': {
                'DEFAULT': [
                    ['nova-key1', 'value1'],
                    ['nova-key2', 'value2'],
                    ['nova-key3', 'value3'],
                    ['nova-key4', 'value4']]
            }}
        )

    def test_syslog_context(self):
        self.config.side_effect = fake_config({'use-syslog': 'foo'})
        syslog = context.SyslogContext()
        result = syslog()
        expected = {
            'use_syslog': 'foo',
        }
        self.assertEquals(result, expected)

    def test_loglevel_context_set(self):
        self.config.side_effect = fake_config({
            'debug': True,
            'verbose': True,
        })
        syslog = context.LogLevelContext()
        result = syslog()
        expected = {
            'debug': True,
            'verbose': True,
        }
        self.assertEquals(result, expected)

    def test_loglevel_context_unset(self):
        self.config.side_effect = fake_config({
            'debug': None,
            'verbose': None,
        })
        syslog = context.LogLevelContext()
        result = syslog()
        expected = {
            'debug': False,
            'verbose': False,
        }
        self.assertEquals(result, expected)

    def test_zeromq_context_unrelated(self):
        self.is_relation_made.return_value = False
        self.assertEquals(context.ZeroMQContext()(), {})

    def test_zeromq_context_related(self):
        self.is_relation_made.return_value = True
        self.relation_ids.return_value = ['zeromq-configuration:1']
        self.related_units.return_value = ['openstack-zeromq/0']
        self.relation_get.side_effect = ['nonce-data', 'hostname', 'redis']
        self.assertEquals(context.ZeroMQContext()(),
                          {'zmq_host': 'hostname',
                           'zmq_nonce': 'nonce-data',
                           'zmq_redis_address': 'redis'})

    def test_notificationdriver_context_nomsg(self):
        relations = {
            'zeromq-configuration': False,
            'amqp': False,
        }
        rels = fake_is_relation_made(relations=relations)
        self.is_relation_made.side_effect = rels.rel_made
        self.assertEquals(context.NotificationDriverContext()(),
                          {'notifications': 'False'})

    def test_notificationdriver_context_zmq_nometer(self):
        relations = {
            'zeromq-configuration': True,
            'amqp': False,
        }
        rels = fake_is_relation_made(relations=relations)
        self.is_relation_made.side_effect = rels.rel_made
        self.assertEquals(context.NotificationDriverContext()(),
                          {'notifications': 'False'})

    def test_notificationdriver_context_zmq_meter(self):
        relations = {
            'zeromq-configuration': True,
            'amqp': False,
        }
        rels = fake_is_relation_made(relations=relations)
        self.is_relation_made.side_effect = rels.rel_made
        self.assertEquals(context.NotificationDriverContext()(),
                          {'notifications': 'False'})

    def test_notificationdriver_context_amq(self):
        relations = {
            'zeromq-configuration': False,
            'amqp': True,
        }
        rels = fake_is_relation_made(relations=relations)
        self.is_relation_made.side_effect = rels.rel_made
        self.assertEquals(context.NotificationDriverContext()(),
                          {'notifications': 'True'})

    def test_workerconfig_context_noconfig(self):
        self.config.return_value = None
        with patch.object(context.WorkerConfigContext, 'num_cpus', 2):
            worker = context.WorkerConfigContext()
            self.assertEqual({'workers': 0}, worker())

    def test_workerconfig_context_withconfig(self):
        self.config.side_effect = fake_config({
            'worker-multiplier': 4,
        })
        with patch.object(context.WorkerConfigContext, 'num_cpus', 2):
            worker = context.WorkerConfigContext()
            self.assertEqual({'workers': 8}, worker())

    def test_apache_get_addresses_no_network_splits(self):
        self.https.return_value = True
        self.config.side_effect = fake_config({
            'vip': '10.5.1.1 10.5.2.1 10.5.3.1',
            'os-internal-network': None,
            'os-admin-network': None,
            'os-public-network': None
        })
        self.is_clustered.side_effect = [True, True, True]
        self.get_address_in_network.side_effect = ['10.5.1.100',
                                                   '10.5.2.100',
                                                   '10.5.3.100']

        self.unit_get.return_value = '10.5.1.50'
        apache = context.ApacheSSLContext()
        apache.external_ports = '8776'

        addresses = apache.get_network_addresses()
        expected = []
        self.assertEqual(addresses, expected)

        calls = [call(None, '10.5.1.50'),
                 call(None, '10.5.1.50'),
                 call(None, '10.5.1.50')]
        self.get_address_in_network.assert_has_calls(calls)

    def test_apache_get_addresses_no_vips_no_networks(self):
        self.https.return_value = True
        self.config.side_effect = fake_config({
            'vip': '',
            'os-internal-network': None,
            'os-admin-network': None,
            'os-public-network': None
        })
        self.is_clustered.side_effect = [True, True, True]
        self.get_address_in_network.side_effect = ['10.5.1.100',
                                                   '10.5.2.100',
                                                   '10.5.3.100']

        self.unit_get.return_value = '10.5.1.50'
        apache = context.ApacheSSLContext()

        addresses = apache.get_network_addresses()
        expected = [('10.5.1.100', '10.5.1.100'),
                    ('10.5.2.100', '10.5.2.100'),
                    ('10.5.3.100', '10.5.3.100')]
        self.assertEqual(addresses, expected)

        calls = [call(None, '10.5.1.50'),
                 call(None, '10.5.1.50'),
                 call(None, '10.5.1.50')]
        self.get_address_in_network.assert_has_calls(calls)

    def test_apache_get_addresses_no_vips_w_networks(self):
        self.https.return_value = True
        self.config.side_effect = fake_config({
            'vip': '',
            'os-internal-network': '10.5.1.0/24',
            'os-admin-network': '10.5.2.0/24',
            'os-public-network': '10.5.3.0/24',
        })
        self.is_clustered.side_effect = [True, True, True]
        self.get_address_in_network.side_effect = ['10.5.1.100',
                                                   '10.5.2.100',
                                                   '10.5.3.100']

        self.unit_get.return_value = '10.5.1.50'
        apache = context.ApacheSSLContext()

        addresses = apache.get_network_addresses()
        expected = [('10.5.1.100', '10.5.1.100'),
                    ('10.5.2.100', '10.5.2.100'),
                    ('10.5.3.100', '10.5.3.100')]
        self.assertEqual(addresses, expected)

        calls = [call('10.5.1.0/24', '10.5.1.50'),
                 call('10.5.2.0/24', '10.5.1.50'),
                 call('10.5.3.0/24', '10.5.1.50')]
        self.get_address_in_network.assert_has_calls(calls)

    def test_apache_get_addresses_with_network_splits(self):
        self.https.return_value = True
        self.config.side_effect = fake_config({
            'vip': '10.5.1.1 10.5.2.1 10.5.3.1',
            'os-internal-network': '10.5.1.0/24',
            'os-admin-network': '10.5.2.0/24',
            'os-public-network': '10.5.3.0/24',
        })
        self.is_clustered.side_effect = [True, True, True]
        self.get_address_in_network.side_effect = ['10.5.1.100',
                                                   '10.5.2.100',
                                                   '10.5.3.100']

        self.unit_get.return_value = '10.5.1.50'
        apache = context.ApacheSSLContext()
        apache.external_ports = '8776'

        addresses = apache.get_network_addresses()
        expected = [('10.5.1.100', '10.5.1.1'),
                    ('10.5.2.100', '10.5.2.1'),
                    ('10.5.3.100', '10.5.3.1')]

        self.assertEqual(addresses, expected)

        calls = [call('10.5.1.0/24', '10.5.1.50'),
                 call('10.5.2.0/24', '10.5.1.50'),
                 call('10.5.3.0/24', '10.5.1.50')]
        self.get_address_in_network.assert_has_calls(calls)

    def test_apache_get_addresses_with_missing_network(self):
        self.https.return_value = True
        self.config.side_effect = fake_config({
            'vip': '10.5.1.1 10.5.2.1 10.5.3.1',
            'os-internal-network': '10.5.1.0/24',
            'os-admin-network': '10.5.2.0/24',
            'os-public-network': '',
        })
        self.is_clustered.side_effect = [True, True, True]
        self.get_address_in_network.side_effect = ['10.5.1.100',
                                                   '10.5.2.100',
                                                   '10.5.1.50']

        self.unit_get.return_value = '10.5.1.50'
        apache = context.ApacheSSLContext()
        apache.external_ports = '8776'

        addresses = apache.get_network_addresses()
        expected = [('10.5.1.100', '10.5.1.1'),
                    ('10.5.2.100', '10.5.2.1')]

        self.assertEqual(addresses, expected)

        calls = [call('10.5.1.0/24', '10.5.1.50'),
                 call('10.5.2.0/24', '10.5.1.50')]
        self.get_address_in_network.assert_has_calls(calls)

    def test_apache_get_addresses_with_network_splits_ipv6(self):
        self.https.return_value = True
        self.config.side_effect = fake_config({
            'vip': ('2001:db8::5001 2001:db9::5001 2001:dba::5001'),
            'os-internal-network': '2001:db8::/113',
            'os-admin-network': '2001:db9::/113',
            'os-public-network': '2001:dba::/113',
        })
        self.is_clustered.side_effect = [True, True, True]
        self.get_address_in_network.side_effect = ['2001:db8::5100',
                                                   '2001:db9::5100',
                                                   '2001:dba::5100']

        self.unit_get.return_value = '2001:db8::5050'
        apache = context.ApacheSSLContext()
        apache.external_ports = '8776'

        addresses = apache.get_network_addresses()
        expected = [('2001:db8::5100', '2001:db8::5001'),
                    ('2001:db9::5100', '2001:db9::5001'),
                    ('2001:dba::5100', '2001:dba::5001')]

        self.assertEqual(addresses, expected)

        calls = [call('2001:db8::/113', '2001:db8::5050'),
                 call('2001:db9::/113', '2001:db8::5050'),
                 call('2001:dba::/113', '2001:db8::5050')]
        self.get_address_in_network.assert_has_calls(calls)

    def test_config_flag_parsing_simple(self):
        # Standard key=value checks...
        flags = context.config_flags_parser('key1=value1, key2=value2')
        self.assertEqual(flags, {'key1': 'value1', 'key2': 'value2'})

        # Check for multiple values to a single key
        flags = context.config_flags_parser('key1=value1, '
                                            'key2=value2,value3,value4')
        self.assertEqual(flags, {'key1': 'value1',
                                 'key2': 'value2,value3,value4'})

        # Check for yaml formatted key value pairings for more complex
        # assignment options.
        flags = context.config_flags_parser('key1: subkey1=value1,'
                                            'subkey2=value2')
        self.assertEqual(flags, {'key1': 'subkey1=value1,subkey2=value2'})

        # Check for good measure the ldap formats
        test_string = ('user_tree_dn: ou=ABC General,'
                       'ou=User Accounts,dc=example,dc=com')
        flags = context.config_flags_parser(test_string)
        self.assertEqual(flags, {'user_tree_dn': ('ou=ABC General,'
                                                  'ou=User Accounts,'
                                                  'dc=example,dc=com')})

    def _fake_get_hwaddr(self, arg):
        return MACHINE_MACS[arg]

    def _fake_get_ipv4(self, arg, fatal=False):
        return MACHINE_NICS[arg]

    @patch('charmhelpers.contrib.openstack.context.config')
    def test_no_ext_port(self, mock_config):
        self.config.side_effect = config = fake_config({})
        mock_config.side_effect = config
        self.assertEquals(context.ExternalPortContext()(), {})

    @patch('charmhelpers.contrib.openstack.context.config')
    def test_ext_port_eth(self, mock_config):
        config = fake_config({'ext-port': 'eth1010'})
        self.config.side_effect = config
        mock_config.side_effect = config
        self.assertEquals(context.ExternalPortContext()(),
                          {'ext_port': 'eth1010'})

    @patch('charmhelpers.contrib.openstack.context.is_phy_iface',
           lambda arg: True)
    @patch('charmhelpers.contrib.openstack.context.get_nic_hwaddr')
    @patch('charmhelpers.contrib.openstack.context.list_nics')
    @patch('charmhelpers.contrib.openstack.context.get_ipv6_addr')
    @patch('charmhelpers.contrib.openstack.context.get_ipv4_addr')
    @patch('charmhelpers.contrib.openstack.context.config')
    def test_ext_port_mac(self, mock_config, mock_get_ipv4_addr,
                          mock_get_ipv6_addr, mock_list_nics,
                          mock_get_nic_hwaddr):
        config_macs = ABSENT_MACS + " " + MACHINE_MACS['eth2']
        config = fake_config({'ext-port': config_macs})
        self.config.side_effect = config
        mock_config.side_effect = config

        mock_get_ipv4_addr.side_effect = self._fake_get_ipv4
        mock_get_ipv6_addr.return_value = []
        mock_list_nics.return_value = MACHINE_MACS.keys()
        mock_get_nic_hwaddr.side_effect = self._fake_get_hwaddr

        self.assertEquals(context.ExternalPortContext()(),
                          {'ext_port': 'eth2'})

        config = fake_config({'ext-port': ABSENT_MACS})
        self.config.side_effect = config
        mock_config.side_effect = config

        self.assertEquals(context.ExternalPortContext()(), {})

    @patch('charmhelpers.contrib.openstack.context.is_phy_iface',
           lambda arg: True)
    @patch('charmhelpers.contrib.openstack.context.get_nic_hwaddr')
    @patch('charmhelpers.contrib.openstack.context.list_nics')
    @patch('charmhelpers.contrib.openstack.context.get_ipv6_addr')
    @patch('charmhelpers.contrib.openstack.context.get_ipv4_addr')
    @patch('charmhelpers.contrib.openstack.context.config')
    def test_ext_port_mac_one_used_nic(self, mock_config,
                                       mock_get_ipv4_addr,
                                       mock_get_ipv6_addr, mock_list_nics,
                                       mock_get_nic_hwaddr):

        self.relation_ids.return_value = ['neutron-plugin-api:1']
        self.related_units.return_value = ['neutron-api/0']
        self.relation_get.return_value = {'network-device-mtu': 1234,
                                          'l2-population': 'False'}
        config_macs = "%s %s" % (MACHINE_MACS['eth1'],
                                 MACHINE_MACS['eth2'])

        mock_get_ipv4_addr.side_effect = self._fake_get_ipv4
        mock_get_ipv6_addr.return_value = []
        mock_list_nics.return_value = MACHINE_MACS.keys()
        mock_get_nic_hwaddr.side_effect = self._fake_get_hwaddr

        config = fake_config({'ext-port': config_macs})
        self.config.side_effect = config
        mock_config.side_effect = config
        self.assertEquals(context.ExternalPortContext()(),
                          {'ext_port': 'eth2', 'ext_port_mtu': 1234})

    @patch('charmhelpers.contrib.openstack.context.NeutronPortContext.'
           'resolve_ports')
    def test_data_port_eth(self, mock_resolve):
        self.config.side_effect = fake_config({'data-port':
                                               'phybr1:eth1010 '
                                               'phybr1:eth1011'})
        mock_resolve.side_effect = lambda ports: ['eth1010']
        self.assertEquals(context.DataPortContext()(),
                          {'eth1010': 'phybr1'})

    @patch.object(context, 'get_nic_hwaddr')
    @patch.object(context.NeutronPortContext, 'resolve_ports')
    def test_data_port_mac(self, mock_resolve, mock_get_nic_hwaddr):
        extant_mac = 'cb:23:ae:72:f2:33'
        non_extant_mac = 'fa:16:3e:12:97:8e'
        self.config.side_effect = fake_config({'data-port':
                                               'phybr1:%s phybr1:%s' %
                                               (non_extant_mac, extant_mac)})

        def fake_resolve(ports):
            resolved = []
            for port in ports:
                if port == extant_mac:
                    resolved.append('eth1010')

            return resolved

        mock_get_nic_hwaddr.side_effect = lambda nic: extant_mac
        mock_resolve.side_effect = fake_resolve

        self.assertEquals(context.DataPortContext()(),
                          {'eth1010': 'phybr1'})

    @patch.object(context.NeutronAPIContext, '__call__', lambda *args:
                  {'network_device_mtu': 5000})
    @patch.object(context, 'get_nic_hwaddr', lambda inst, port: port)
    @patch.object(context.NeutronPortContext, 'resolve_ports',
                  lambda inst, ports: ports)
    def test_phy_nic_mtu_context(self):
        self.config.side_effect = fake_config({'data-port':
                                               'phybr1:eth0'})
        ctxt = context.PhyNICMTUContext()()
        self.assertEqual(ctxt, {'devs': 'eth0', 'mtu': 5000})

    @patch.object(context.glob, 'glob')
    @patch.object(context.NeutronAPIContext, '__call__', lambda *args:
                  {'network_device_mtu': 5000})
    @patch.object(context, 'get_nic_hwaddr', lambda inst, port: port)
    @patch.object(context.NeutronPortContext, 'resolve_ports',
                  lambda inst, ports: ports)
    def test_phy_nic_mtu_context_vlan(self, mock_glob):
        self.config.side_effect = fake_config({'data-port':
                                               'phybr1:eth0.100'})
        mock_glob.return_value = ['/sys/class/net/eth0.100/lower_eth0']
        ctxt = context.PhyNICMTUContext()()
        self.assertEqual(ctxt, {'devs': 'eth0\\neth0.100', 'mtu': 5000})

    @patch.object(context.glob, 'glob')
    @patch.object(context.NeutronAPIContext, '__call__', lambda *args:
                  {'network_device_mtu': 5000})
    @patch.object(context, 'get_nic_hwaddr', lambda inst, port: port)
    @patch.object(context.NeutronPortContext, 'resolve_ports',
                  lambda inst, ports: ports)
    def test_phy_nic_mtu_context_vlan_w_duplicate_raw(self, mock_glob):
        self.config.side_effect = fake_config({'data-port':
                                               'phybr1:eth0.100 '
                                               'phybr1:eth0.200'})

        def fake_glob(wcard):
            if 'eth0.100' in wcard:
                return ['/sys/class/net/eth0.100/lower_eth0']
            elif 'eth0.200' in wcard:
                return ['/sys/class/net/eth0.200/lower_eth0']

            raise Exception("Unexpeced key '%s'" % (wcard))

        mock_glob.side_effect = fake_glob
        ctxt = context.PhyNICMTUContext()()
        self.assertEqual(ctxt, {'devs': 'eth0\\neth0.100\\neth0.200',
                                'mtu': 5000})

    def test_neutronapicontext_defaults(self):
        self.relation_ids.return_value = []
        expected_keys = [
            'l2_population', 'enable_dvr', 'enable_l3ha',
            'overlay_network_type', 'network_device_mtu'
        ]
        api_ctxt = context.NeutronAPIContext()()
        for key in expected_keys:
            self.assertTrue(key in api_ctxt)

    def test_neutronapicontext_string_converted(self):
        self.relation_ids.return_value = ['neutron-plugin-api:1']
        self.related_units.return_value = ['neutron-api/0']
        self.relation_get.return_value = {'l2-population': 'True'}
        api_ctxt = context.NeutronAPIContext()()
        self.assertEquals(api_ctxt['l2_population'], True)

    def test_neutronapicontext_none(self):
        self.relation_ids.return_value = ['neutron-plugin-api:1']
        self.related_units.return_value = ['neutron-api/0']
        self.relation_get.return_value = {'l2-population': 'True'}
        api_ctxt = context.NeutronAPIContext()()
        self.assertEquals(api_ctxt['network_device_mtu'], None)

    def test_network_service_ctxt_no_units(self):
        self.relation_ids.return_value = []
        self.relation_ids.return_value = ['foo']
        self.related_units.return_value = []
        self.assertEquals(context.NetworkServiceContext()(), {})

    @patch.object(context.OSContextGenerator, 'context_complete')
    def test_network_service_ctxt_no_data(self, mock_context_complete):
        rel = FakeRelation(QUANTUM_NETWORK_SERVICE_RELATION)
        self.relation_ids.side_effect = rel.relation_ids
        self.related_units.side_effect = rel.relation_units
        relation = FakeRelation(relation_data=QUANTUM_NETWORK_SERVICE_RELATION)
        self.relation_get.side_effect = relation.get
        mock_context_complete.return_value = False
        self.assertEquals(context.NetworkServiceContext()(), {})

    def test_network_service_ctxt_data(self):
        data_result = {
            'keystone_host': '10.5.0.1',
            'service_port': '5000',
            'auth_port': '20000',
            'service_tenant': 'tenant',
            'service_username': 'username',
            'service_password': 'password',
            'quantum_host': '10.5.0.2',
            'quantum_port': '9696',
            'quantum_url': 'http://10.5.0.2:9696/v2',
            'region': 'aregion',
            'service_protocol': 'http',
            'auth_protocol': 'http',
        }
        rel = FakeRelation(QUANTUM_NETWORK_SERVICE_RELATION)
        self.relation_ids.side_effect = rel.relation_ids
        self.related_units.side_effect = rel.relation_units
        relation = FakeRelation(relation_data=QUANTUM_NETWORK_SERVICE_RELATION)
        self.relation_get.side_effect = relation.get
        self.assertEquals(context.NetworkServiceContext()(), data_result)
