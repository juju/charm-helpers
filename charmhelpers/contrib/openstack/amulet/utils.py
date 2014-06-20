import logging

import glanceclient.v1.client as glance_client
import keystoneclient.v2_0 as keystone_client
import novaclient.v1_1.client as nova_client

from charmhelpers.contrib.amulet.utils import (
    AmuletUtils
)

DEBUG = logging.DEBUG
ERROR = logging.ERROR


class OpenStackAmuletUtils(AmuletUtils):
    """This class inherits from AmuletUtils and has additional support
       that is specifically for use by OpenStack charms."""

    def __init__(self, log_level=ERROR):
        """Initialize the deployment environment."""
        super(OpenStackAmuletUtils, self).__init__(log_level)

    def validate_endpoint_data(self, endpoints, admin_port, internal_port,
                               public_port, expected):
        """Validate actual endpoint data vs expected endpoint data. The ports
           are used to find the matching endpoint."""
        found = False
        for ep in endpoints:
            self.log.debug('endpoint: {}'.format(repr(ep)))
            if admin_port in ep.adminurl and internal_port in ep.internalurl \
               and public_port in ep.publicurl:
                found = True
                actual = {'id': ep.id,
                          'region': ep.region,
                          'adminurl': ep.adminurl,
                          'internalurl': ep.internalurl,
                          'publicurl': ep.publicurl,
                          'service_id': ep.service_id}
                ret = self._validate_dict_data(expected, actual)
                if ret:
                    return 'unexpected endpoint data - {}'.format(ret)

        if not found:
            return 'endpoint not found'

    def validate_svc_catalog_endpoint_data(self, expected, actual):
        """Validate a list of actual service catalog endpoints vs a list of
           expected service catalog endpoints."""
        self.log.debug('actual: {}'.format(repr(actual)))
        for k, v in expected.iteritems():
            if k in actual:
                ret = self._validate_dict_data(expected[k][0], actual[k][0])
                if ret:
                    return self.endpoint_error(k, ret)
            else:
                return "endpoint {} does not exist".format(k)
        return ret

    def validate_tenant_data(self, expected, actual):
        """Validate a list of actual tenant data vs list of expected tenant
           data."""
        self.log.debug('actual: {}'.format(repr(actual)))
        for e in expected:
            found = False
            for act in actual:
                a = {'enabled': act.enabled, 'description': act.description,
                     'name': act.name, 'id': act.id}
                if e['name'] == a['name']:
                    found = True
                    ret = self._validate_dict_data(e, a)
                    if ret:
                        return "unexpected tenant data - {}".format(ret)
            if not found:
                return "tenant {} does not exist".format(e.name)
        return ret

    def validate_role_data(self, expected, actual):
        """Validate a list of actual role data vs a list of expected role
           data."""
        self.log.debug('actual: {}'.format(repr(actual)))
        for e in expected:
            found = False
            for act in actual:
                a = {'name': act.name, 'id': act.id}
                if e['name'] == a['name']:
                    found = True
                    ret = self._validate_dict_data(e, a)
                    if ret:
                        return "unexpected role data - {}".format(ret)
            if not found:
                return "role {} does not exist".format(e.name)
        return ret

    def validate_user_data(self, expected, actual):
        """Validate a list of actual user data vs a list of expected user
           data."""
        self.log.debug('actual: {}'.format(repr(actual)))
        for e in expected:
            found = False
            for act in actual:
                a = {'enabled': act.enabled, 'name': act.name,
                     'email': act.email, 'tenantId': act.tenantId,
                     'id': act.id}
                if e['name'] == a['name']:
                    found = True
                    ret = self._validate_dict_data(e, a)
                    if ret:
                        return "unexpected user data - {}".format(ret)
            if not found:
                return "user {} does not exist".format(e.name)
        return ret

    def validate_flavor_data(self, expected, actual):
        """Validate a list of actual flavors vs a list of expected flavors."""
        self.log.debug('actual: {}'.format(repr(actual)))
        act = [a.name for a in actual]
        return self._validate_list_data(expected, act)

    def tenant_exists(self, keystone, tenant):
        """Return True if tenant exists"""
        return tenant in [t.name for t in keystone.tenants.list()]

    def authenticate_keystone_admin(self, keystone_sentry, user, password,
                                    tenant):
        """Authenticates admin user with the keystone admin endpoint."""
        service_ip = \
            keystone_sentry.relation('shared-db',
                                     'mysql:shared-db')['private-address']
        ep = "http://{}:35357/v2.0".format(service_ip.strip().decode('utf-8'))
        return keystone_client.Client(username=user, password=password,
                                      tenant_name=tenant, auth_url=ep)

    def authenticate_keystone_user(self, keystone, user, password, tenant):
        """Authenticates a regular user with the keystone public endpoint."""
        ep = keystone.service_catalog.url_for(service_type='identity',
                                              endpoint_type='publicURL')
        return keystone_client.Client(username=user, password=password,
                                      tenant_name=tenant, auth_url=ep)

    def authenticate_glance_admin(self, keystone):
        """Authenticates admin user with glance."""
        ep = keystone.service_catalog.url_for(service_type='image',
                                              endpoint_type='adminURL')
        return glance_client.Client(ep, token=keystone.auth_token)

    def authenticate_nova_user(self, keystone, user, password, tenant):
        """Authenticates a regular user with nova-api."""
        ep = keystone.service_catalog.url_for(service_type='identity',
                                              endpoint_type='publicURL')
        return nova_client.Client(username=user, api_key=password,
                                  project_id=tenant, auth_url=ep)
