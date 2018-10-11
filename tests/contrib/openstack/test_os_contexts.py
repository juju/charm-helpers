import collections
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

SHARED_DB_RELATION_ALT_RID = {
    'mysql-alt:0': {
        'mysql-alt/0': {
            'db_host': 'dbserver-alt.local',
            'password': 'flump'}}}

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
    'service_domain': 'admin_domain',
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
    'service_domain': 'admin_domain',
    'service_tenant': 'admin',
    'service_password': 'foo',
    'service_username': 'adam',
}

IDENTITY_CREDENTIALS_RELATION_UNSET = {
    'credentials_port': '5000',
    'credentials_host': 'keystonehost.local',
    'auth_host': 'keystone-host.local',
    'auth_port': '35357',
    'auth_protocol': 'https',
    'domain': 'admin_domain',
    'credentials_project': 'admin',
    'credentials_project_id': '123456',
    'credentials_password': 'foo',
    'credentials_username': 'adam',
    'credentials_protocol': 'https',
}


APIIDENTITY_SERVICE_RELATION_UNSET = {
    'neutron-plugin-api:0': {
        'neutron-api/0': {
            'service_port': '5000',
            'service_host': 'keystonehost.local',
            'auth_host': 'keystone-host.local',
            'auth_port': '35357',
            'service_domain': 'admin_domain',
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
    'service_domain': 'admin_domain',
    'service_tenant': 'admin',
    'service_password': 'foo',
    'service_username': 'adam',
    'service_protocol': 'https',
    'auth_protocol': 'https',
}

IDENTITY_SERVICE_RELATION_VERSIONED = {
    'api_version': '3',
}
IDENTITY_SERVICE_RELATION_VERSIONED.update(IDENTITY_SERVICE_RELATION_HTTPS)

IDENTITY_CREDENTIALS_RELATION_VERSIONED = {
    'api_version': '3',
    'service_domain_id': '567890',
}
IDENTITY_CREDENTIALS_RELATION_VERSIONED.update(IDENTITY_CREDENTIALS_RELATION_UNSET)

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
    'service_domain': 'admin_domain',
    'service_tenant': 'admin',
    'service_password': 'foo',
    'service_username': 'adam',
}

AMQP_RELATION = {
    'private-address': 'rabbithost',
    'password': 'foobar',
    'vip': '10.0.0.1',
}

AMQP_RELATION_ALT_RID = {
    'amqp-alt:0': {
        'rabbitmq-alt/0': {
            'private-address': 'rabbitalthost1',
            'password': 'flump',
        },
    }
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
    'oslo-messaging-flags': ("rabbit_max_retries=1"
                             ",rabbit_retry_backoff=1"
                             ",rabbit_retry_interval=1")
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
            'use_syslog': 'true'
        },
        'ceph/1': {
            'private-address': 'ceph_node2',
            'auth': 'foo',
            'key': 'bar',
            'use_syslog': 'false'
        },
    }
}

CEPH_RELATION_WITH_PUBLIC_ADDR = {
    'ceph:0': {
        'ceph/0': {
            'ceph-public-address': '192.168.1.10',
            'private-address': 'ceph_node1',
            'auth': 'foo',
            'key': 'bar'
        },
        'ceph/1': {
            'ceph-public-address': '192.168.1.11',
            'private-address': 'ceph_node2',
            'auth': 'foo',
            'key': 'bar'
        },
    }
}

CEPH_REL_WITH_PUBLIC_ADDR_PORT = {
    'ceph:0': {
        'ceph/0': {
            'ceph-public-address': '192.168.1.10:1234',
            'private-address': 'ceph_node1',
            'auth': 'foo',
            'key': 'bar'
        },
        'ceph/1': {
            'ceph-public-address': '192.168.1.11:4321',
            'private-address': 'ceph_node2',
            'auth': 'foo',
            'key': 'bar'
        },
    }
}

CEPH_REL_WITH_PUBLIC_IPv6_ADDR = {
    'ceph:0': {
        'ceph/0': {
            'ceph-public-address': '2001:5c0:9168::1',
            'private-address': 'ceph_node1',
            'auth': 'foo',
            'key': 'bar'
        },
        'ceph/1': {
            'ceph-public-address': '2001:5c0:9168::2',
            'private-address': 'ceph_node2',
            'auth': 'foo',
            'key': 'bar'
        },
    }
}

CEPH_REL_WITH_PUBLIC_IPv6_ADDR_PORT = {
    'ceph:0': {
        'ceph/0': {
            'ceph-public-address': '[2001:5c0:9168::1]:1234',
            'private-address': 'ceph_node1',
            'auth': 'foo',
            'key': 'bar'
        },
        'ceph/1': {
            'ceph-public-address': '[2001:5c0:9168::2]:4321',
            'private-address': 'ceph_node2',
            'auth': 'foo',
            'key': 'bar'
        },
    }
}

CEPH_REL_WITH_MULTI_PUBLIC_ADDR = {
    'ceph:0': {
        'ceph/0': {
            'ceph-public-address': '192.168.1.10 192.168.1.20',
            'private-address': 'ceph_node1',
            'auth': 'foo',
            'key': 'bar'
        },
        'ceph/1': {
            'ceph-public-address': '192.168.1.11 192.168.1.21',
            'private-address': 'ceph_node2',
            'auth': 'foo',
            'key': 'bar'
        },
    }
}

CEPH_REL_WITH_DEFAULT_FEATURES = {
    'ceph:0': {
        'ceph/0': {
            'private-address': 'ceph_node1',
            'auth': 'foo',
            'key': 'bar',
            'use_syslog': 'true',
            'rbd-features': '1'
        },
        'ceph/1': {
            'private-address': 'ceph_node2',
            'auth': 'foo',
            'key': 'bar',
            'use_syslog': 'false',
            'rbd-features': '1'
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

QUANTUM_NETWORK_SERVICE_RELATION_VERSIONED = {
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
            'region': 'aregion',
            'api_version': '3',
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

NOVA_SUB_CONFIG3 = """
nova-compute:
    /etc/nova/nova.conf:
        sections:
            DEFAULT:
                - [nova-key5, value5]
                - [nova-key6, value6]
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
            'subordinate_configuration': json.dumps(
                yaml.load(CINDER_SUB_CONFIG1)),
        },
    },
    'cinder-subordinate:1': {
        'cinder-subordinate/1': {
            'private-address': 'cinder_node1',
            'subordinate_configuration': json.dumps(
                yaml.load(CINDER_SUB_CONFIG2)),
        },
    },
}

SUB_CONFIG_RELATION2 = {
    'nova-ceilometer:6': {
        'ceilometer-agent/0': {
            'private-address': 'nova_node1',
            'subordinate_configuration': json.dumps(
                yaml.load(NOVA_SUB_CONFIG1)),
        },
    },
    'neutron-plugin:3': {
        'neutron-ovs-plugin/0': {
            'private-address': 'nova_node1',
            'subordinate_configuration': json.dumps(
                yaml.load(NOVA_SUB_CONFIG2)),
        },
    },
    'neutron-plugin:4': {
        'neutron-other-plugin/0': {
            'private-address': 'nova_node1',
            'subordinate_configuration': json.dumps(
                yaml.load(NOVA_SUB_CONFIG3)),
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
    'is_clustered',
    'time',
    'https',
    'get_address_in_network',
    'get_netmask_for_address',
    'local_unit',
    'get_ipv6_addr',
    'mkdir',
    'write_file',
    'get_relation_ip',
    'charm_name',
    'sysctl_create',
    'kv',
    'pwgen',
    'lsb_release',
    'is_container',
    'network_get_primary_address',
    'resolve_address',
    'is_ipv6_disabled',
    'snap_install_requested',
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


class TestDB(object):
    '''Test KV store for unitdata testing'''
    def __init__(self):
        self.data = {}
        self.flushed = False

    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value):
        self.data[key] = value
        return value

    def flush(self):
        self.flushed = True


class ContextTests(unittest.TestCase):

    def setUp(self):
        for m in TO_PATCH:
            setattr(self, m, self._patch(m))
        # mock at least a single relation + unit
        self.relation_ids.return_value = ['foo:0']
        self.related_units.return_value = ['foo/0']
        self.local_unit.return_value = 'localunit'
        self.kv.side_effect = TestDB
        self.pwgen.return_value = 'testpassword'
        self.lsb_release.return_value = {'DISTRIB_RELEASE': '16.04'}
        self.is_container.return_value = False
        self.network_get_primary_address.side_effect = NotImplementedError()
        self.resolve_address.return_value = '10.5.1.50'
        self.snap_install_requested.return_value = False
        self.maxDiff = None

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
        """Mismatch between hostname and hostname for access net - defers
        execution"""
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
        """Correctly set hostname for access net returns complete context"""
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

    def test_shared_db_context_explicit_relation_id(self):
        '''Test shared-db context setting the relation_id'''
        relation = FakeRelation(relation_data=SHARED_DB_RELATION_ALT_RID)
        self.related_units.return_value = ['mysql-alt/0']
        self.relation_get.side_effect = relation.get
        self.get_address_in_network.return_value = ''
        self.config.side_effect = fake_config(SHARED_DB_CONFIG)
        shared_db = context.SharedDBContext(relation_id='mysql-alt:0')
        result = shared_db()
        expected = {
            'database_host': 'dbserver-alt.local',
            'database': 'foodb',
            'database_user': 'adam',
            'database_password': 'flump',
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
            call(expected['database_ssl_ca'], 'wb'),
            call(expected['database_ssl_cert'], 'wb'),
            call(expected['database_ssl_key'], 'wb')
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

    @patch('charmhelpers.contrib.openstack.context.format_ipv6_addr')
    def test_shared_db_context_with_ipv6(self, format_ipv6_addr):
        '''Test shared-db context with ipv6'''
        shared_db = context.SharedDBContext(
            database='quantum', user='quantum', relation_prefix='quantum')
        relation = FakeRelation(relation_data=SHARED_DB_RELATION_NAMESPACED)
        self.relation_get.side_effect = relation.get
        format_ipv6_addr.return_value = '[2001:db8:1::1]'
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
            'admin_domain_id': None,
            'admin_user': 'adam',
            'auth_host': 'keystone-host.local',
            'auth_port': '35357',
            'auth_protocol': 'http',
            'service_host': 'keystonehost.local',
            'service_port': '5000',
            'service_protocol': 'http',
            'api_version': '2.0',
        }
        self.assertEquals(result, expected)

    def test_identity_credentials_context_with_data(self):
        '''Test identity-credentials context with all required data'''
        relation = FakeRelation(relation_data=IDENTITY_CREDENTIALS_RELATION_UNSET)
        self.relation_get.side_effect = relation.get
        identity_credentials = context.IdentityCredentialsContext()
        result = identity_credentials()
        expected = {
            'admin_password': 'foo',
            'admin_tenant_name': 'admin',
            'admin_tenant_id': '123456',
            'admin_user': 'adam',
            'auth_host': 'keystone-host.local',
            'auth_port': '35357',
            'auth_protocol': 'https',
            'service_host': 'keystonehost.local',
            'service_port': '5000',
            'service_protocol': 'https',
            'api_version': '2.0',
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
            'admin_domain_id': None,
            'admin_user': 'adam',
            'auth_host': 'keystone-host.local',
            'auth_port': '35357',
            'auth_protocol': 'http',
            'service_host': 'keystonehost.local',
            'service_port': '5000',
            'service_protocol': 'http',
            'api_version': '2.0',
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
            'admin_domain_id': None,
            'admin_user': 'adam',
            'auth_host': 'keystone-host.local',
            'auth_port': '35357',
            'auth_protocol': 'http',
            'service_host': 'keystonehost.local',
            'service_port': '5000',
            'service_protocol': 'http',
            'signing_dir': '/var/cache/cinder',
            'api_version': '2.0',
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
            'admin_domain_id': None,
            'admin_user': 'adam',
            'auth_host': 'keystone-host.local',
            'auth_port': '35357',
            'auth_protocol': 'http',
            'service_host': 'keystonehost.local',
            'service_port': '5000',
            'service_protocol': 'http',
            'api_version': '2.0',
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
            'admin_domain_id': None,
            'admin_user': 'adam',
            'auth_host': 'keystone-host.local',
            'auth_port': '35357',
            'auth_protocol': 'https',
            'service_host': 'keystonehost.local',
            'service_port': '5000',
            'service_protocol': 'https',
            'api_version': '2.0',
        }
        self.assertEquals(result, expected)

    def test_identity_service_context_with_data_versioned(self):
        '''Test shared-db context with api version supplied from keystone'''
        relation = FakeRelation(
            relation_data=IDENTITY_SERVICE_RELATION_VERSIONED)
        self.relation_get.side_effect = relation.get
        identity_service = context.IdentityServiceContext()
        result = identity_service()
        expected = {
            'admin_password': 'foo',
            'admin_domain_name': 'admin_domain',
            'admin_tenant_name': 'admin',
            'admin_tenant_id': None,
            'admin_domain_id': None,
            'admin_user': 'adam',
            'auth_host': 'keystone-host.local',
            'auth_port': '35357',
            'auth_protocol': 'https',
            'service_host': 'keystonehost.local',
            'service_port': '5000',
            'service_protocol': 'https',
            'api_version': '3',
        }
        self.assertEquals(result, expected)

    def test_identity_credentials_context_with_data_versioned(self):
        '''Test identity-credentials context with api version supplied from keystone'''
        relation = FakeRelation(
            relation_data=IDENTITY_CREDENTIALS_RELATION_VERSIONED)
        self.relation_get.side_effect = relation.get
        identity_credentials = context.IdentityCredentialsContext()
        result = identity_credentials()
        expected = {
            'admin_password': 'foo',
            'admin_domain_name': 'admin_domain',
            'admin_tenant_name': 'admin',
            'admin_tenant_id': '123456',
            'admin_user': 'adam',
            'auth_host': 'keystone-host.local',
            'auth_port': '35357',
            'auth_protocol': 'https',
            'service_host': 'keystonehost.local',
            'service_port': '5000',
            'service_protocol': 'https',
            'api_version': '3',
        }
        self.assertEquals(result, expected)

    @patch('charmhelpers.contrib.openstack.context.format_ipv6_addr')
    def test_identity_service_context_with_ipv6(self, format_ipv6_addr):
        '''Test identity-service context with ipv6'''
        relation = FakeRelation(relation_data=IDENTITY_SERVICE_RELATION_HTTP)
        self.relation_get.side_effect = relation.get
        format_ipv6_addr.return_value = '[2001:db8:1::1]'
        identity_service = context.IdentityServiceContext()
        result = identity_service()
        expected = {
            'admin_password': 'foo',
            'admin_tenant_name': 'admin',
            'admin_tenant_id': '123456',
            'admin_domain_id': None,
            'admin_user': 'adam',
            'auth_host': '[2001:db8:1::1]',
            'auth_port': '35357',
            'auth_protocol': 'http',
            'service_host': '[2001:db8:1::1]',
            'service_port': '5000',
            'service_protocol': 'http',
            'api_version': '2.0',
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
            'rabbitmq_virtual_host': 'foo',
            'transport_url': 'rabbit://adam:foobar@rabbithost:5672/foo'
        }
        self.assertEquals(result, expected)

    def test_amqp_context_explicit_relation_id(self):
        '''Test amqp context setting the relation_id'''
        relation = FakeRelation(relation_data=AMQP_RELATION_ALT_RID)
        self.relation_get.side_effect = relation.get
        self.related_units.return_value = ['rabbitmq-alt/0']
        self.config.return_value = AMQP_CONFIG
        amqp = context.AMQPContext(relation_id='amqp-alt:0')
        result = amqp()
        expected = {
            'rabbitmq_host': 'rabbitalthost1',
            'rabbitmq_password': 'flump',
            'rabbitmq_user': 'adam',
            'rabbitmq_virtual_host': 'foo',
            'transport_url': 'rabbit://adam:flump@rabbitalthost1:5672/foo'
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
            'rabbitmq_virtual_host': 'foo',
            'transport_url': 'rabbit://adam:foobar@rabbithost:5672/foo'
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
            'transport_url': 'rabbit://adam:foobar@rabbithost:5671/foo'
        }
        _open.assert_called_once_with(ssl_dir + '/rabbit-client-ca.pem', 'wb')
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
            'transport_url': 'rabbit://adam:foobar@rabbithost:5671/foo'
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
            'transport_url': 'rabbit://adam:foobar@10.0.0.1:5672/foo'
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
            'transport_url': ('rabbit://adam:foobar@rabbithost1:5672'
                              ',adam:foobar@rabbithost2:5672/foo')
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

    @patch('charmhelpers.contrib.openstack.context.format_ipv6_addr')
    def test_amqp_context_with_ipv6(self, format_ipv6_addr):
        '''Test amqp context with ipv6'''
        relation_data = copy(AMQP_AA_RELATION)
        relation = FakeRelation(relation_data=relation_data)
        self.relation_get.side_effect = relation.get
        self.relation_ids.side_effect = relation.relation_ids
        self.related_units.side_effect = relation.relation_units
        format_ipv6_addr.return_value = '[2001:db8:1::1]'
        self.config.return_value = AMQP_CONFIG
        amqp = context.AMQPContext()
        result = amqp()
        expected = {
            'rabbitmq_host': '[2001:db8:1::1]',
            'rabbitmq_password': 'foobar',
            'rabbitmq_user': 'adam',
            'rabbitmq_virtual_host': 'foo',
            'rabbitmq_hosts': '[2001:db8:1::1],[2001:db8:1::1]',
            'transport_url': ('rabbit://adam:foobar@[2001:db8:1::1]:5672'
                              ',adam:foobar@[2001:db8:1::1]:5672/foo')
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
            'transport_url': 'rabbit://adam:foobar@rabbithost:5672/foo'
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
            'use_syslog': 'true',
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
            'use_syslog': 'true',
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
    def test_ceph_context_with_public_addr_and_port(
            self, ensure_packages, mkdir, isdir, mock_config):
        '''Test ceph context in host with multiple networks with all
        relation data'''
        isdir.return_value = False
        config_dict = {'use-syslog': True}

        def fake_config(key):
            return config_dict.get(key)

        mock_config.side_effect = fake_config
        relation = FakeRelation(relation_data=CEPH_REL_WITH_PUBLIC_ADDR_PORT)
        self.relation_get.side_effect = relation.get
        self.relation_ids.side_effect = relation.relation_ids
        self.related_units.side_effect = relation.relation_units
        ceph = context.CephContext()
        result = ceph()
        expected = {
            'mon_hosts': '192.168.1.10:1234 192.168.1.11:4321',
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
    def test_ceph_context_with_public_ipv6_addr(self, ensure_packages, mkdir,
                                                isdir, mock_config):
        '''Test ceph context in host with multiple networks with all
        relation data'''
        isdir.return_value = False
        config_dict = {'use-syslog': True}

        def fake_config(key):
            return config_dict.get(key)

        mock_config.side_effect = fake_config
        relation = FakeRelation(relation_data=CEPH_REL_WITH_PUBLIC_IPv6_ADDR)
        self.relation_get.side_effect = relation.get
        self.relation_ids.side_effect = relation.relation_ids
        self.related_units.side_effect = relation.relation_units
        ceph = context.CephContext()
        result = ceph()
        expected = {
            'mon_hosts': '[2001:5c0:9168::1] [2001:5c0:9168::2]',
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
    def test_ceph_context_with_public_ipv6_addr_port(
            self, ensure_packages, mkdir, isdir, mock_config):
        '''Test ceph context in host with multiple networks with all
        relation data'''
        isdir.return_value = False
        config_dict = {'use-syslog': True}

        def fake_config(key):
            return config_dict.get(key)

        mock_config.side_effect = fake_config
        relation = FakeRelation(
            relation_data=CEPH_REL_WITH_PUBLIC_IPv6_ADDR_PORT)
        self.relation_get.side_effect = relation.get
        self.relation_ids.side_effect = relation.relation_ids
        self.related_units.side_effect = relation.relation_units
        ceph = context.CephContext()
        result = ceph()
        expected = {
            'mon_hosts': '[2001:5c0:9168::1]:1234 [2001:5c0:9168::2]:4321',
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
    def test_ceph_context_with_multi_public_addr(
            self, ensure_packages, mkdir, isdir, mock_config):
        '''Test ceph context in host with multiple networks with all
        relation data'''
        isdir.return_value = False
        config_dict = {'use-syslog': True}

        def fake_config(key):
            return config_dict.get(key)

        mock_config.side_effect = fake_config
        relation = FakeRelation(relation_data=CEPH_REL_WITH_MULTI_PUBLIC_ADDR)
        self.relation_get.side_effect = relation.get
        self.relation_ids.side_effect = relation.relation_ids
        self.related_units.side_effect = relation.relation_units
        ceph = context.CephContext()
        result = ceph()
        expected = {
            'mon_hosts': '192.168.1.10 192.168.1.11 192.168.1.20 192.168.1.21',
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
    def test_ceph_context_with_default_features(
            self, ensure_packages, mkdir, isdir, mock_config):
        '''Test ceph context in host with multiple networks with all
        relation data'''
        isdir.return_value = False
        config_dict = {'use-syslog': True}

        def fake_config(key):
            return config_dict.get(key)

        mock_config.side_effect = fake_config
        relation = FakeRelation(relation_data=CEPH_REL_WITH_DEFAULT_FEATURES)
        self.relation_get.side_effect = relation.get
        self.relation_ids.side_effect = relation.relation_ids
        self.related_units.side_effect = relation.relation_units
        ceph = context.CephContext()
        result = ceph()
        expected = {
            'mon_hosts': 'ceph_node1 ceph_node2',
            'auth': 'foo',
            'key': 'bar',
            'use_syslog': 'true',
            'rbd_features': '1',
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
        # We are only using get_relation_ip.
        # Setup the values it returns on each subsequent call.
        self.get_relation_ip.side_effect = [None, None, None,
                                            'cluster-peer0.localnet']
        relation = FakeRelation(cluster_relation)
        self.relation_ids.side_effect = relation.relation_ids
        self.relation_get.side_effect = relation.get
        self.related_units.side_effect = relation.relation_units
        self.get_netmask_for_address.return_value = '255.255.0.0'
        self.config.return_value = False
        self.maxDiff = None
        self.is_ipv6_disabled.return_value = True
        haproxy = context.HAProxyContext()
        with patch_open() as (_open, _file):
            result = haproxy()
        ex = {
            'frontends': {
                'cluster-peer0.localnet': {
                    'network': 'cluster-peer0.localnet/255.255.0.0',
                    'backends': collections.OrderedDict([
                        ('peer-0', 'cluster-peer0.localnet'),
                        ('peer-1', 'cluster-peer1.localnet'),
                        ('peer-2', 'cluster-peer2.localnet'),
                    ]),
                },
            },
            'default_backend': 'cluster-peer0.localnet',
            'local_host': '127.0.0.1',
            'haproxy_host': '0.0.0.0',
            'ipv6_enabled': False,
            'stat_password': 'testpassword',
            'stat_port': '8888',
        }
        # the context gets generated.
        self.assertEquals(ex, result)
        # and /etc/default/haproxy is updated.
        self.assertEquals(_file.write.call_args_list,
                          [call('ENABLED=1\n')])
        self.get_relation_ip.assert_has_calls([call('admin', False),
                                               call('internal', False),
                                               call('public', False),
                                               call('cluster')])

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
        # We are only using get_relation_ip.
        # Setup the values it returns on each subsequent call.
        self.get_relation_ip.side_effect = [None, None, None,
                                            'cluster-peer0.localnet']
        relation = FakeRelation(cluster_relation)
        self.relation_ids.side_effect = relation.relation_ids
        self.relation_get.side_effect = relation.get
        self.related_units.side_effect = relation.relation_units
        self.get_netmask_for_address.return_value = '255.255.0.0'
        self.config.return_value = False
        self.maxDiff = None
        c = fake_config(HAPROXY_CONFIG)
        c.data['prefer-ipv6'] = False
        self.config.side_effect = c
        self.is_ipv6_disabled.return_value = True
        haproxy = context.HAProxyContext()
        with patch_open() as (_open, _file):
            result = haproxy()
        ex = {
            'frontends': {
                'cluster-peer0.localnet': {
                    'network': 'cluster-peer0.localnet/255.255.0.0',
                    'backends': collections.OrderedDict([
                        ('peer-0', 'cluster-peer0.localnet'),
                        ('peer-1', 'cluster-peer1.localnet'),
                        ('peer-2', 'cluster-peer2.localnet'),
                    ]),
                }
            },
            'default_backend': 'cluster-peer0.localnet',
            'local_host': '127.0.0.1',
            'haproxy_host': '0.0.0.0',
            'ipv6_enabled': False,
            'stat_password': 'testpassword',
            'stat_port': '8888',
            'haproxy_client_timeout': 50000,
            'haproxy_server_timeout': 50000,
        }
        # the context gets generated.
        self.assertEquals(ex, result)
        # and /etc/default/haproxy is updated.
        self.assertEquals(_file.write.call_args_list,
                          [call('ENABLED=1\n')])
        self.get_relation_ip.assert_has_calls([call('admin', None),
                                               call('internal', None),
                                               call('public', None),
                                               call('cluster')])

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
        relation = FakeRelation(cluster_relation)
        self.relation_ids.side_effect = relation.relation_ids
        self.relation_get.side_effect = relation.get
        self.related_units.side_effect = relation.relation_units
        # We are only using get_relation_ip.
        # Setup the values it returns on each subsequent call.
        self.get_relation_ip.side_effect = ['cluster-peer0.admin',
                                            'cluster-peer0.internal',
                                            'cluster-peer0.public',
                                            'cluster-peer0.localnet']
        self.get_netmask_for_address.return_value = '255.255.0.0'
        self.config.return_value = False
        self.maxDiff = None
        self.is_ipv6_disabled.return_value = True
        haproxy = context.HAProxyContext()
        with patch_open() as (_open, _file):
            result = haproxy()
        ex = {
            'frontends': {
                'cluster-peer0.admin': {
                    'network': 'cluster-peer0.admin/255.255.0.0',
                    'backends': collections.OrderedDict([
                        ('peer-0', 'cluster-peer0.admin'),
                        ('peer-1', 'cluster-peer1.admin'),
                        ('peer-2', 'cluster-peer2.admin'),
                    ]),
                },
                'cluster-peer0.internal': {
                    'network': 'cluster-peer0.internal/255.255.0.0',
                    'backends': collections.OrderedDict([
                        ('peer-0', 'cluster-peer0.internal'),
                        ('peer-1', 'cluster-peer1.internal'),
                        ('peer-2', 'cluster-peer2.internal'),
                    ]),
                },
                'cluster-peer0.public': {
                    'network': 'cluster-peer0.public/255.255.0.0',
                    'backends': collections.OrderedDict([
                        ('peer-0', 'cluster-peer0.public'),
                        ('peer-1', 'cluster-peer1.public'),
                        ('peer-2', 'cluster-peer2.public'),
                    ]),
                },
                'cluster-peer0.localnet': {
                    'network': 'cluster-peer0.localnet/255.255.0.0',
                    'backends': collections.OrderedDict([
                        ('peer-0', 'cluster-peer0.localnet'),
                        ('peer-1', 'cluster-peer1.localnet'),
                        ('peer-2', 'cluster-peer2.localnet'),
                    ]),
                }
            },
            'default_backend': 'cluster-peer0.localnet',
            'local_host': '127.0.0.1',
            'haproxy_host': '0.0.0.0',
            'ipv6_enabled': False,
            'stat_password': 'testpassword',
            'stat_port': '8888',
        }
        # the context gets generated.
        self.assertEquals(ex, result)
        # and /etc/default/haproxy is updated.
        self.assertEquals(_file.write.call_args_list,
                          [call('ENABLED=1\n')])
        self.get_relation_ip.assert_has_calls([call('admin', False),
                                               call('internal', False),
                                               call('public', False),
                                               call('cluster')])

    @patch('charmhelpers.contrib.openstack.context.unit_get')
    @patch('charmhelpers.contrib.openstack.context.local_unit')
    def test_haproxy_context_with_data_public_only(self, local_unit, unit_get):
        '''Test haproxy context with with openstack-dashboard public only binding'''
        cluster_relation = {
            'cluster:0': {
                'peer/1': {
                    'private-address': 'cluster-peer1.localnet',
                    'public-address': 'cluster-peer1.public',
                },
                'peer/2': {
                    'private-address': 'cluster-peer2.localnet',
                    'public-address': 'cluster-peer2.public',
                },
            },
        }

        local_unit.return_value = 'peer/0'
        relation = FakeRelation(cluster_relation)
        self.relation_ids.side_effect = relation.relation_ids
        self.relation_get.side_effect = relation.get
        self.related_units.side_effect = relation.relation_units
        # We are only using get_relation_ip.
        # Setup the values it returns on each subsequent call.
        _network_get_map = {
            'public': 'cluster-peer0.public',
            'cluster': 'cluster-peer0.localnet',
        }
        self.get_relation_ip.side_effect = (
            lambda binding, config_opt=None:
                _network_get_map[binding]
        )
        self.get_netmask_for_address.return_value = '255.255.0.0'
        self.config.return_value = None
        self.maxDiff = None
        self.is_ipv6_disabled.return_value = True
        haproxy = context.HAProxyContext(address_types=['public'])
        with patch_open() as (_open, _file):
            result = haproxy()
        ex = {
            'frontends': {
                'cluster-peer0.public': {
                    'network': 'cluster-peer0.public/255.255.0.0',
                    'backends': collections.OrderedDict([
                        ('peer-0', 'cluster-peer0.public'),
                        ('peer-1', 'cluster-peer1.public'),
                        ('peer-2', 'cluster-peer2.public'),
                    ]),
                },
                'cluster-peer0.localnet': {
                    'network': 'cluster-peer0.localnet/255.255.0.0',
                    'backends': collections.OrderedDict([
                        ('peer-0', 'cluster-peer0.localnet'),
                        ('peer-1', 'cluster-peer1.localnet'),
                        ('peer-2', 'cluster-peer2.localnet'),
                    ]),
                }
            },
            'default_backend': 'cluster-peer0.localnet',
            'local_host': '127.0.0.1',
            'haproxy_host': '0.0.0.0',
            'ipv6_enabled': False,
            'stat_password': 'testpassword',
            'stat_port': '8888',
        }
        # the context gets generated.
        self.assertEquals(ex, result)
        # and /etc/default/haproxy is updated.
        self.assertEquals(_file.write.call_args_list,
                          [call('ENABLED=1\n')])
        self.get_relation_ip.assert_has_calls([call('public', None),
                                               call('cluster')])

    @patch('charmhelpers.contrib.openstack.context.unit_get')
    @patch('charmhelpers.contrib.openstack.context.local_unit')
    def test_haproxy_context_with_data_ipv6(self, local_unit, unit_get):
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
        # We are only using get_relation_ip.
        # Setup the values it returns on each subsequent call.
        self.get_relation_ip.side_effect = [None, None, None,
                                            'cluster-peer0.localnet']
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
        self.is_ipv6_disabled.return_value = False
        haproxy = context.HAProxyContext()
        with patch_open() as (_open, _file):
            result = haproxy()
        ex = {
            'frontends': {
                'cluster-peer0.localnet': {
                    'network': 'cluster-peer0.localnet/'
                    'FFFF:FFFF:FFFF:FFFF:0000:0000:0000:0000',
                    'backends': collections.OrderedDict([
                        ('peer-0', 'cluster-peer0.localnet'),
                        ('peer-1', 'cluster-peer1.localnet'),
                        ('peer-2', 'cluster-peer2.localnet'),
                    ]),
                }
            },
            'default_backend': 'cluster-peer0.localnet',
            'local_host': 'ip6-localhost',
            'haproxy_server_timeout': 50000,
            'haproxy_client_timeout': 50000,
            'haproxy_host': '::',
            'ipv6_enabled': True,
            'stat_password': 'testpassword',
            'stat_port': '8888',
        }
        # the context gets generated.
        self.assertEquals(ex, result)
        # and /etc/default/haproxy is updated.
        self.assertEquals(_file.write.call_args_list,
                          [call('ENABLED=1\n')])
        self.get_relation_ip.assert_has_calls([call('admin', None),
                                               call('internal', None),
                                               call('public', None),
                                               call('cluster')])

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
        # We are only using get_relation_ip.
        # Setup the values it returns on each subsequent call.
        self.get_relation_ip.side_effect = [None, None, None, None]
        relation = FakeRelation(cluster_relation)
        self.relation_ids.side_effect = relation.relation_ids
        self.relation_get.side_effect = relation.get
        self.related_units.side_effect = relation.relation_units
        self.config.return_value = False
        haproxy = context.HAProxyContext()
        self.assertEquals({}, haproxy())
        self.get_relation_ip.assert_has_calls([call('admin', False),
                                               call('internal', False),
                                               call('public', False),
                                               call('cluster')])

    @patch('charmhelpers.contrib.openstack.context.unit_get')
    @patch('charmhelpers.contrib.openstack.context.local_unit')
    def test_haproxy_context_with_net_override(self, local_unit, unit_get):
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
        # We are only using get_relation_ip.
        # Setup the values it returns on each subsequent call.
        self.get_relation_ip.side_effect = [None, None, None, None]
        relation = FakeRelation(cluster_relation)
        self.relation_ids.side_effect = relation.relation_ids
        self.relation_get.side_effect = relation.get
        self.related_units.side_effect = relation.relation_units
        self.config.return_value = False
        c = fake_config(HAPROXY_CONFIG)
        c.data['os-admin-network'] = '192.168.10.0/24'
        c.data['os-internal-network'] = '192.168.20.0/24'
        c.data['os-public-network'] = '192.168.30.0/24'
        self.config.side_effect = c
        haproxy = context.HAProxyContext()
        self.assertEquals({}, haproxy())
        self.get_relation_ip.assert_has_calls([call('admin', '192.168.10.0/24'),
                                               call('internal', '192.168.20.0/24'),
                                               call('public', '192.168.30.0/24'),
                                               call('cluster')])

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
        # We are only using get_relation_ip.
        # Setup the values it returns on each subsequent call.
        self.get_relation_ip.side_effect = [None, None, None,
                                            'lonely.clusterpeer.howsad']
        relation = FakeRelation(cluster_relation)
        self.relation_ids.side_effect = relation.relation_ids
        self.relation_get.side_effect = relation.get
        self.related_units.side_effect = relation.relation_units
        self.config.return_value = False
        self.get_address_in_network.return_value = None
        self.get_netmask_for_address.return_value = '255.255.0.0'
        self.is_ipv6_disabled.return_value = True
        with patch_open() as (_open, _file):
            result = context.HAProxyContext(singlenode_mode=True)()
        ex = {
            'frontends': {
                'lonely.clusterpeer.howsad': {
                    'backends': collections.OrderedDict([
                        ('peer-0', 'lonely.clusterpeer.howsad')]),
                    'network': 'lonely.clusterpeer.howsad/255.255.0.0'
                },
            },
            'default_backend': 'lonely.clusterpeer.howsad',
            'haproxy_host': '0.0.0.0',
            'local_host': '127.0.0.1',
            'ipv6_enabled': False,
            'stat_port': '8888',
            'stat_password': 'testpassword',
        }
        self.assertEquals(ex, result)
        # and /etc/default/haproxy is updated.
        self.assertEquals(_file.write.call_args_list,
                          [call('ENABLED=1\n')])
        self.get_relation_ip.assert_has_calls([call('admin', False),
                                               call('internal', False),
                                               call('public', False),
                                               call('cluster')])

    def test_https_context_with_no_https(self):
        '''Test apache2 https when no https data available'''
        apache = context.ApacheSSLContext()
        self.https.return_value = False
        self.assertEquals({}, apache())

    def _https_context_setup(self):
        '''
        Helper for test_https_context* tests.

        '''
        self.https.return_value = True
        self.determine_api_port.return_value = 8756
        self.determine_apache_port.return_value = 8766

        apache = context.ApacheSSLContext()
        apache.configure_cert = MagicMock()
        apache.enable_modules = MagicMock()
        apache.configure_ca = MagicMock()
        apache.canonical_names = MagicMock()
        apache.canonical_names.return_value = [
            '10.5.1.1',
            '10.5.2.1',
            '10.5.3.1',
        ]
        apache.get_network_addresses = MagicMock()
        apache.get_network_addresses.return_value = [
            ('10.5.1.100', '10.5.1.1'),
            ('10.5.2.100', '10.5.2.1'),
            ('10.5.3.100', '10.5.3.1'),
        ]
        apache.external_ports = '8776'
        apache.service_namespace = 'cinder'

        ex = {
            'namespace': 'cinder',
            'endpoints': [('10.5.1.100', '10.5.1.1', 8766, 8756),
                          ('10.5.2.100', '10.5.2.1', 8766, 8756),
                          ('10.5.3.100', '10.5.3.1', 8766, 8756)],
            'ext_ports': [8766]
        }

        return apache, ex

    def test_https_context(self):
        self.relation_ids.return_value = []

        apache, ex = self._https_context_setup()

        self.assertEquals(ex, apache())

        apache.configure_cert.assert_has_calls([
            call('10.5.1.1'),
            call('10.5.2.1'),
            call('10.5.3.1')
        ])

        self.assertTrue(apache.configure_ca.called)
        self.assertTrue(apache.enable_modules.called)
        self.assertTrue(apache.configure_cert.called)

    def test_https_context_vault_relation(self):
        self.relation_ids.return_value = ['certificates:2']
        self.related_units.return_value = 'vault/0'

        apache, ex = self._https_context_setup()

        self.assertEquals(ex, apache())

        self.assertFalse(apache.configure_cert.called)
        self.assertFalse(apache.configure_ca.called)

    def test_https_context_no_canonical_names(self):
        self.relation_ids.return_value = []

        apache, ex = self._https_context_setup()
        apache.canonical_names.return_value = []

        self.resolve_address.side_effect = (
            '10.5.1.4', '10.5.2.5', '10.5.3.6')

        self.assertEquals(ex, apache())

        apache.configure_cert.assert_has_calls([
            call('10.5.1.4'),
            call('10.5.2.5'),
            call('10.5.3.6')
        ])

        self.resolve_address.assert_has_calls([
            call(endpoint_type=context.INTERNAL),
            call(endpoint_type=context.ADMIN),
            call(endpoint_type=context.PUBLIC),
        ])

        self.assertTrue(apache.configure_ca.called)
        self.assertTrue(apache.enable_modules.called)
        self.assertTrue(apache.configure_cert.called)

    def test_https_context_loads_correct_apache_mods(self):
        # Test apache2 context also loads required apache modules
        apache = context.ApacheSSLContext()
        apache.enable_modules()
        ex_cmd = ['a2enmod', 'ssl', 'proxy', 'proxy_http', 'headers']
        self.check_call.assert_called_with(ex_cmd)

    def test_https_configure_cert(self):
        # Test apache2 properly installs certs and keys to disk
        self.get_cert.return_value = ('SSL_CERT', 'SSL_KEY')
        self.b64decode.side_effect = [b'SSL_CERT', b'SSL_KEY']
        apache = context.ApacheSSLContext()
        apache.service_namespace = 'cinder'
        apache.configure_cert('test-cn')
        # appropriate directories are created.
        self.mkdir.assert_called_with(path='/etc/apache2/ssl/cinder')
        # appropriate files are written.
        files = [call(path='/etc/apache2/ssl/cinder/cert_test-cn',
                      content=b'SSL_CERT', perms=0o640),
                 call(path='/etc/apache2/ssl/cinder/key_test-cn',
                      content=b'SSL_KEY', perms=0o640)]
        self.write_file.assert_has_calls(files)
        # appropriate bits are b64decoded.
        decode = [call('SSL_CERT'), call('SSL_KEY')]
        self.assertEquals(decode, self.b64decode.call_args_list)

    def test_https_configure_cert_deprecated(self):
        # Test apache2 properly installs certs and keys to disk
        self.get_cert.return_value = ('SSL_CERT', 'SSL_KEY')
        self.b64decode.side_effect = ['SSL_CERT', 'SSL_KEY']
        apache = context.ApacheSSLContext()
        apache.service_namespace = 'cinder'
        apache.configure_cert()
        # appropriate directories are created.
        self.mkdir.assert_called_with(path='/etc/apache2/ssl/cinder')
        # appropriate files are written.
        files = [call(path='/etc/apache2/ssl/cinder/cert',
                      content='SSL_CERT', perms=0o640),
                 call(path='/etc/apache2/ssl/cinder/key',
                      content='SSL_KEY', perms=0o640)]
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
    @patch.object(context.NeutronContext, 'ovs_ctxt')
    @patch.object(context.NeutronContext, 'plugin')
    @patch.object(context.NeutronContext, '_ensure_packages')
    @patch.object(context.NeutronContext, 'network_manager')
    def test_neutron_main_context_generation(self, mock_network_manager,
                                             mock_ensure_packages,
                                             mock_plugin, mock_ovs_ctxt,
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
    @patch.object(context.NeutronContext, 'nvp_ctxt')
    @patch.object(context.NeutronContext, 'plugin')
    @patch.object(context.NeutronContext, '_ensure_packages')
    @patch.object(context.NeutronContext, 'network_manager')
    def test_neutron_main_context_gen_nvp_and_alchemy(self,
                                                      mock_network_manager,
                                                      mock_ensure_packages,
                                                      mock_plugin,
                                                      mock_nvp_ctxt,
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
    @patch.object(context.NeutronContext, 'calico_ctxt')
    @patch.object(context.NeutronContext, 'plugin')
    @patch.object(context.NeutronContext, '_ensure_packages')
    @patch.object(context.NeutronContext, 'network_manager')
    def test_neutron_main_context_gen_calico(self, mock_network_manager,
                                             mock_ensure_packages,
                                             mock_plugin, mock_ovs_ctxt,
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

    @patch('charmhelpers.contrib.openstack.utils.juju_log',
           lambda *args, **kwargs: None)
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
                    ['nova-key4', 'value4'],
                    ['nova-key5', 'value5'],
                    ['nova-key6', 'value6']]
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

    @patch.object(context, '_calculate_workers')
    def test_wsgi_worker_config_context(self,
                                        _calculate_workers):
        self.config.return_value = 2  # worker-multiplier=2
        _calculate_workers.return_value = 8
        service_name = 'service-name'
        script = '/usr/bin/script'
        ctxt = context.WSGIWorkerConfigContext(name=service_name,
                                               script=script)
        expect = {
            "service_name": service_name,
            "user": service_name,
            "group": service_name,
            "script": script,
            "admin_script": None,
            "public_script": None,
            "processes": 8,
            "admin_processes": 2,
            "public_processes": 6,
            "threads": 1,
        }
        self.assertEqual(expect, ctxt())

    @patch.object(context, '_calculate_workers')
    def test_wsgi_worker_config_context_user_and_group(self,
                                                       _calculate_workers):
        self.config.return_value = 1
        _calculate_workers.return_value = 1
        service_name = 'service-name'
        script = '/usr/bin/script'
        user = 'nova'
        group = 'nobody'
        ctxt = context.WSGIWorkerConfigContext(name=service_name,
                                               user=user,
                                               group=group,
                                               script=script)
        expect = {
            "service_name": service_name,
            "user": user,
            "group": group,
            "script": script,
            "admin_script": None,
            "public_script": None,
            "processes": 1,
            "admin_processes": 1,
            "public_processes": 1,
            "threads": 1,
        }
        self.assertEqual(expect, ctxt())

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

    @patch.object(context, 'psutil')
    def test_num_cpus_xenial(self, _psutil):
        _psutil.cpu_count.return_value = 4
        self.assertTrue(context._num_cpus(), 4)

    @patch.object(context, 'psutil')
    def test_num_cpus_trusty(self, _psutil):
        _psutil.NUM_CPUS = 4
        self.assertTrue(context._num_cpus(), 4)

    @patch.object(context, '_num_cpus')
    def test_calculate_workers_float(self, _num_cpus):
        self.config.side_effect = fake_config({
            'worker-multiplier': 0.3
        })
        _num_cpus.return_value = 4
        self.assertTrue(context._calculate_workers(), 4)

    @patch.object(context, '_num_cpus')
    def test_calculate_workers_not_quite_0(self, _num_cpus):
        # Make sure that the multiplier evaluating to somewhere between
        # 0 and 1 in the floating point range still has at least one
        # worker.
        self.config.side_effect = fake_config({
            'worker-multiplier': 0.001
        })
        _num_cpus.return_value = 100
        self.assertTrue(context._calculate_workers(), 1)

    @patch.object(context, 'psutil')
    def test_calculate_workers_0(self, _psutil):
        self.config.side_effect = fake_config({
            'worker-multiplier': 0
        })
        _psutil.cpu_count.return_value = 2
        self.assertTrue(context._calculate_workers(), 0)

    @patch.object(context, '_num_cpus')
    def test_calculate_workers_noconfig(self, _num_cpus):
        self.config.return_value = None
        _num_cpus.return_value = 1
        self.assertTrue(context._calculate_workers(), 2)

    @patch.object(context, '_num_cpus')
    def test_calculate_workers_noconfig_container(self, _num_cpus):
        self.config.return_value = None
        self.is_container.return_value = True
        _num_cpus.return_value = 1
        self.assertTrue(context._calculate_workers(), 2)

    @patch.object(context, '_num_cpus')
    def test_calculate_workers_noconfig_lotsa_cpus_container(self,
                                                             _num_cpus):
        self.config.return_value = None
        self.is_container.return_value = True
        _num_cpus.return_value = 32
        self.assertTrue(context._calculate_workers(), 4)

    @patch.object(context, '_num_cpus')
    def test_calculate_workers_noconfig_lotsa_cpus_not_container(self,
                                                                 _num_cpus):
        self.config.return_value = None
        _num_cpus.return_value = 32
        self.assertTrue(context._calculate_workers(), 64)

    @patch.object(context, '_calculate_workers', return_value=256)
    def test_worker_context(self, calculate_workers):
        self.assertEqual(context.WorkerConfigContext()(),
                         {'workers': 256})

    def test_apache_get_addresses_no_network_config(self):
        self.config.side_effect = fake_config({
            'os-internal-network': None,
            'os-admin-network': None,
            'os-public-network': None
        })
        self.resolve_address.return_value = '10.5.1.50'
        self.unit_get.return_value = '10.5.1.50'

        apache = context.ApacheSSLContext()
        apache.external_ports = '8776'

        addresses = apache.get_network_addresses()
        expected = [('10.5.1.50', '10.5.1.50')]

        self.assertEqual(addresses, expected)

        self.get_address_in_network.assert_not_called()
        self.resolve_address.assert_has_calls([
            call(context.INTERNAL),
            call(context.ADMIN),
            call(context.PUBLIC)
        ])

    def test_apache_get_addresses_with_network_config(self):
        self.config.side_effect = fake_config({
            'os-internal-network': '10.5.1.0/24',
            'os-admin-network': '10.5.2.0/24',
            'os-public-network': '10.5.3.0/24',
        })
        _base_addresses = ['10.5.1.100',
                           '10.5.2.100',
                           '10.5.3.100']
        self.get_address_in_network.side_effect = _base_addresses
        self.resolve_address.side_effect = _base_addresses
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
        self.resolve_address.assert_has_calls([
            call(context.INTERNAL),
            call(context.ADMIN),
            call(context.PUBLIC)
        ])

    def test_apache_get_addresses_network_spaces(self):
        self.config.side_effect = fake_config({
            'os-internal-network': None,
            'os-admin-network': None,
            'os-public-network': None
        })
        self.network_get_primary_address.side_effect = None
        self.network_get_primary_address.return_value = '10.5.2.50'
        self.resolve_address.return_value = '10.5.2.100'
        self.unit_get.return_value = '10.5.1.50'

        apache = context.ApacheSSLContext()
        apache.external_ports = '8776'

        addresses = apache.get_network_addresses()
        expected = [('10.5.2.50', '10.5.2.100')]

        self.assertEqual(addresses, expected)

        self.get_address_in_network.assert_not_called()
        self.resolve_address.assert_has_calls([
            call(context.INTERNAL),
            call(context.ADMIN),
            call(context.PUBLIC)
        ])

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
            'overlay_network_type', 'network_device_mtu',
            'enable_qos', 'enable_nsg_logging'
        ]
        api_ctxt = context.NeutronAPIContext()()
        for key in expected_keys:
            self.assertTrue(key in api_ctxt)
        self.assertEquals(api_ctxt['polling_interval'], 2)
        self.assertEquals(api_ctxt['rpc_response_timeout'], 60)
        self.assertEquals(api_ctxt['report_interval'], 30)
        self.assertEquals(api_ctxt['enable_nsg_logging'], False)

    def setup_neutron_api_context_relation(self, cfg):
        self.relation_ids.return_value = ['neutron-plugin-api:1']
        self.related_units.return_value = ['neutron-api/0']
        # The l2-population key is used by the context as a way of checking if
        # the api service on the other end is sending data in a recent format.
        self.relation_get.return_value = cfg

    def test_neutronapicontext_extension_drivers_qos_on(self):
        self.setup_neutron_api_context_relation({
            'enable-qos': 'True',
            'l2-population': 'True'})
        api_ctxt = context.NeutronAPIContext()()
        self.assertTrue(api_ctxt['enable_qos'])
        self.assertEquals(api_ctxt['extension_drivers'], 'qos')

    def test_neutronapicontext_extension_drivers_qos_off(self):
        self.setup_neutron_api_context_relation({
            'enable-qos': 'False',
            'l2-population': 'True'})
        api_ctxt = context.NeutronAPIContext()()
        self.assertFalse(api_ctxt['enable_qos'])
        self.assertEquals(api_ctxt['extension_drivers'], '')

    def test_neutronapicontext_extension_drivers_qos_absent(self):
        self.setup_neutron_api_context_relation({
            'l2-population': 'True'})
        api_ctxt = context.NeutronAPIContext()()
        self.assertFalse(api_ctxt['enable_qos'])
        self.assertEquals(api_ctxt['extension_drivers'], '')

    def test_neutronapicontext_extension_drivers_log_off(self):
        self.setup_neutron_api_context_relation({
            'enable-nsg-logging': 'False',
            'l2-population': 'True'})
        api_ctxt = context.NeutronAPIContext()()
        self.assertEquals(api_ctxt['extension_drivers'], '')

    def test_neutronapicontext_extension_drivers_log_on(self):
        self.setup_neutron_api_context_relation({
            'enable-nsg-logging': 'True',
            'l2-population': 'True'})
        api_ctxt = context.NeutronAPIContext()()
        self.assertEquals(api_ctxt['extension_drivers'], 'log')

    def test_neutronapicontext_extension_drivers_log_qos_on(self):
        self.setup_neutron_api_context_relation({
            'enable-qos': 'True',
            'enable-nsg-logging': 'True',
            'l2-population': 'True'})
        api_ctxt = context.NeutronAPIContext()()
        self.assertEquals(api_ctxt['extension_drivers'], 'qos,log')

    def test_neutronapicontext_string_converted(self):
        self.setup_neutron_api_context_relation({
            'l2-population': 'True'})
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
            'api_version': '2.0',
        }
        rel = FakeRelation(QUANTUM_NETWORK_SERVICE_RELATION)
        self.relation_ids.side_effect = rel.relation_ids
        self.related_units.side_effect = rel.relation_units
        relation = FakeRelation(relation_data=QUANTUM_NETWORK_SERVICE_RELATION)
        self.relation_get.side_effect = relation.get
        self.assertEquals(context.NetworkServiceContext()(), data_result)

    def test_network_service_ctxt_data_api_version(self):
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
            'api_version': '3',
        }
        rel = FakeRelation(QUANTUM_NETWORK_SERVICE_RELATION_VERSIONED)
        self.relation_ids.side_effect = rel.relation_ids
        self.related_units.side_effect = rel.relation_units
        relation = FakeRelation(
            relation_data=QUANTUM_NETWORK_SERVICE_RELATION_VERSIONED)
        self.relation_get.side_effect = relation.get
        self.assertEquals(context.NetworkServiceContext()(), data_result)

    def test_internal_endpoint_context(self):
        config = {'use-internal-endpoints': False}
        self.config.side_effect = fake_config(config)
        ctxt = context.InternalEndpointContext()
        self.assertFalse(ctxt()['use_internal_endpoints'])
        config = {'use-internal-endpoints': True}
        self.config.side_effect = fake_config(config)
        self.assertTrue(ctxt()['use_internal_endpoints'])

    @patch.object(context, 'os_release')
    def test_volume_api_context(self, mock_os_release):
        mock_os_release.return_value = 'ocata'
        config = {'use-internal-endpoints': False}
        self.config.side_effect = fake_config(config)
        ctxt = context.VolumeAPIContext('cinder-common')
        c = ctxt()
        self.assertEqual(c['volume_api_version'], '2')
        self.assertEqual(c['volume_catalog_info'],
                         'volumev2:cinderv2:publicURL')

        mock_os_release.return_value = 'pike'
        config['use-internal-endpoints'] = True
        self.config.side_effect = fake_config(config)
        ctxt = context.VolumeAPIContext('cinder-common')
        c = ctxt()
        self.assertEqual(c['volume_api_version'], '3')
        self.assertEqual(c['volume_catalog_info'],
                         'volumev3:cinderv3:internalURL')

    def test_volume_api_context_no_pkg(self):
        self.assertRaises(ValueError, context.VolumeAPIContext, "")
        self.assertRaises(ValueError, context.VolumeAPIContext, None)

    def test_apparmor_context_call_not_valid(self):
        ''' Tests for the apparmor context'''
        mock_aa_object = context.AppArmorContext()
        # Test with invalid config
        self.config.return_value = 'NOTVALID'
        self.assertEquals(mock_aa_object.__call__(), None)

    def test_apparmor_context_call_complain(self):
        ''' Tests for the apparmor context'''
        mock_aa_object = context.AppArmorContext()
        # Test complain mode
        self.config.return_value = 'complain'
        self.assertEquals(mock_aa_object.__call__(),
                          {'aa_profile_mode': 'complain',
                           'ubuntu_release': '16.04'})

    def test_apparmor_context_call_enforce(self):
        ''' Tests for the apparmor context'''
        mock_aa_object = context.AppArmorContext()
        # Test enforce mode
        self.config.return_value = 'enforce'
        self.assertEquals(mock_aa_object.__call__(),
                          {'aa_profile_mode': 'enforce',
                           'ubuntu_release': '16.04'})

    def test_apparmor_context_call_disable(self):
        ''' Tests for the apparmor context'''
        mock_aa_object = context.AppArmorContext()
        # Test complain mode
        self.config.return_value = 'disable'
        self.assertEquals(mock_aa_object.__call__(),
                          {'aa_profile_mode': 'disable',
                           'ubuntu_release': '16.04'})

    def test_apparmor_setup_complain(self):
        ''' Tests for the apparmor setup'''
        AA = context.AppArmorContext(profile_name='fake-aa-profile')
        AA.install_aa_utils = MagicMock()
        AA.manually_disable_aa_profile = MagicMock()
        # Test complain mode
        self.config.return_value = 'complain'
        AA.setup_aa_profile()
        AA.install_aa_utils.assert_called_with()
        self.check_call.assert_called_with(['aa-complain', 'fake-aa-profile'])
        self.assertFalse(AA.manually_disable_aa_profile.called)

    def test_apparmor_setup_enforce(self):
        ''' Tests for the apparmor setup'''
        AA = context.AppArmorContext(profile_name='fake-aa-profile')
        AA.install_aa_utils = MagicMock()
        AA.manually_disable_aa_profile = MagicMock()
        # Test enforce mode
        self.config.return_value = 'enforce'
        AA.setup_aa_profile()
        self.check_call.assert_called_with(['aa-enforce', 'fake-aa-profile'])
        self.assertFalse(AA.manually_disable_aa_profile.called)

    def test_apparmor_setup_disable(self):
        ''' Tests for the apparmor setup'''
        AA = context.AppArmorContext(profile_name='fake-aa-profile')
        AA.install_aa_utils = MagicMock()
        AA.manually_disable_aa_profile = MagicMock()
        # Test disable mode
        self.config.return_value = 'disable'
        AA.setup_aa_profile()
        self.check_call.assert_called_with(['aa-disable', 'fake-aa-profile'])
        self.assertFalse(AA.manually_disable_aa_profile.called)
        # Test failed to disable
        from subprocess import CalledProcessError
        self.check_call.side_effect = CalledProcessError(0, 0, 0)
        AA.setup_aa_profile()
        self.check_call.assert_called_with(['aa-disable', 'fake-aa-profile'])
        AA.manually_disable_aa_profile.assert_called_with()

    @patch.object(context, 'enable_memcache')
    @patch.object(context, 'is_ipv6_disabled')
    def test_memcache_context_ipv6(self, _is_ipv6_disabled, _enable_memcache):
        self.lsb_release.return_value = {'DISTRIB_CODENAME': 'xenial'}
        _enable_memcache.return_value = True
        _is_ipv6_disabled.return_value = False
        config = {
            'openstack-origin': 'distro',
        }
        self.config.side_effect = fake_config(config)
        ctxt = context.MemcacheContext()
        self.assertTrue(ctxt()['use_memcache'])
        expect = {
            'memcache_port': '11211',
            'memcache_server': '::1',
            'memcache_server_formatted': '[::1]',
            'memcache_url': 'inet6:[::1]:11211',
            'use_memcache': True}
        self.assertEqual(ctxt(), expect)
        self.lsb_release.return_value = {'DISTRIB_CODENAME': 'trusty'}
        expect['memcache_server'] = 'ip6-localhost'
        ctxt = context.MemcacheContext()
        self.assertEqual(ctxt(), expect)

    @patch.object(context, 'enable_memcache')
    @patch.object(context, 'is_ipv6_disabled')
    def test_memcache_context_ipv4(self, _is_ipv6_disabled, _enable_memcache):
        self.lsb_release.return_value = {'DISTRIB_CODENAME': 'xenial'}
        _enable_memcache.return_value = True
        _is_ipv6_disabled.return_value = True
        config = {
            'openstack-origin': 'distro',
        }
        self.config.side_effect = fake_config(config)
        ctxt = context.MemcacheContext()
        self.assertTrue(ctxt()['use_memcache'])
        expect = {
            'memcache_port': '11211',
            'memcache_server': '127.0.0.1',
            'memcache_server_formatted': '127.0.0.1',
            'memcache_url': '127.0.0.1:11211',
            'use_memcache': True}
        self.assertEqual(ctxt(), expect)
        self.lsb_release.return_value = {'DISTRIB_CODENAME': 'trusty'}
        expect['memcache_server'] = 'localhost'
        ctxt = context.MemcacheContext()
        self.assertEqual(ctxt(), expect)

    @patch.object(context, 'enable_memcache')
    def test_memcache_off_context(self, _enable_memcache):
        _enable_memcache.return_value = False
        config = {'openstack-origin': 'distro'}
        self.config.side_effect = fake_config(config)
        ctxt = context.MemcacheContext()
        self.assertFalse(ctxt()['use_memcache'])
        self.assertEqual(ctxt(), {'use_memcache': False})

    @patch('charmhelpers.contrib.openstack.context.mkdir')
    def test_ensure_dir_ctx(self, mkdir):
        dirname = '/etc/keystone/policy.d'
        owner = 'someuser'
        group = 'somegroup'
        perms = 0o555
        force = False
        ctxt = context.EnsureDirContext(dirname, owner=owner,
                                        group=group, perms=perms,
                                        force=force)
        ctxt()
        mkdir.assert_called_with(dirname, owner=owner, group=group,
                                 perms=perms, force=force)

    @patch.object(context, 'os_release')
    def test_VersionsContext(self, os_release):
        self.lsb_release.return_value = {'DISTRIB_CODENAME': 'xenial'}
        os_release.return_value = 'essex'
        self.assertEqual(
            context.VersionsContext()(),
            {
                'openstack_release': 'essex',
                'operating_system_release': 'xenial'})
        os_release.assert_called_once_with('python-keystone', base='icehouse')
        self.lsb_release.assert_called_once_with()
