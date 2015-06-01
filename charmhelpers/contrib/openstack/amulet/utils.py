# Copyright 2014-2015 Canonical Limited.
#
# This file is part of charm-helpers.
#
# charm-helpers is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version 3 as
# published by the Free Software Foundation.
#
# charm-helpers is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with charm-helpers.  If not, see <http://www.gnu.org/licenses/>.

import logging
import os
import six
import time
import urllib

import glanceclient.v1.client as glance_client
import heatclient.v1.client as heat_client
import keystoneclient.v2_0 as keystone_client
import novaclient.v1_1.client as nova_client

from time import sleep
from charmhelpers.contrib.amulet.utils import (
    AmuletUtils
)

DEBUG = logging.DEBUG
ERROR = logging.ERROR


class OpenStackAmuletUtils(AmuletUtils):
    """OpenStack amulet utilities.

       This class inherits from AmuletUtils and has additional support
       that is specifically for use by OpenStack charm tests.
       """

    def __init__(self, log_level=ERROR):
        """Initialize the deployment environment."""
        super(OpenStackAmuletUtils, self).__init__(log_level)

    def validate_endpoint_data(self, endpoints, admin_port, internal_port,
                               public_port, expected):
        """Validate endpoint data.

           Validate actual endpoint data vs expected endpoint data. The ports
           are used to find the matching endpoint.
           """
        self.log.debug('Validating endpoint data...')
        found = False
        for ep in endpoints:
            self.log.debug('endpoint: {}'.format(repr(ep)))
            if (admin_port in ep.adminurl and
                    internal_port in ep.internalurl and
                    public_port in ep.publicurl):
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
        """Validate service catalog endpoint data.

           Validate a list of actual service catalog endpoints vs a list of
           expected service catalog endpoints.
           """
        self.log.debug('Validating service catalog endpoint data...')
        self.log.debug('actual: {}'.format(repr(actual)))
        for k, v in six.iteritems(expected):
            if k in actual:
                ret = self._validate_dict_data(expected[k][0], actual[k][0])
                if ret:
                    return self.endpoint_error(k, ret)
            else:
                return "endpoint {} does not exist".format(k)
        return ret

    def validate_tenant_data(self, expected, actual):
        """Validate tenant data.

           Validate a list of actual tenant data vs list of expected tenant
           data.
           """
        self.log.debug('Validating tenant data...')
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
                return "tenant {} does not exist".format(e['name'])
        return ret

    def validate_role_data(self, expected, actual):
        """Validate role data.

           Validate a list of actual role data vs a list of expected role
           data.
           """
        self.log.debug('Validating role data...')
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
                return "role {} does not exist".format(e['name'])
        return ret

    def validate_user_data(self, expected, actual):
        """Validate user data.

           Validate a list of actual user data vs a list of expected user
           data.
           """
        self.log.debug('Validating user data...')
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
                return "user {} does not exist".format(e['name'])
        return ret

    def validate_flavor_data(self, expected, actual):
        """Validate flavor data.

           Validate a list of actual flavors vs a list of expected flavors.
           """
        self.log.debug('Validating flavor data...')
        self.log.debug('actual: {}'.format(repr(actual)))
        act = [a.name for a in actual]
        return self._validate_list_data(expected, act)

    def tenant_exists(self, keystone, tenant):
        """Return True if tenant exists."""
        self.log.debug('Checking if tenant exists ({})...'.format(tenant))
        return tenant in [t.name for t in keystone.tenants.list()]

    def authenticate_keystone_admin(self, keystone_sentry, user, password,
                                    tenant):
        """Authenticates admin user with the keystone admin endpoint."""
        self.log.debug('Authenticating keystone admin...')
        unit = keystone_sentry
        service_ip = unit.relation('shared-db',
                                   'mysql:shared-db')['private-address']
        ep = "http://{}:35357/v2.0".format(service_ip.strip().decode('utf-8'))
        return keystone_client.Client(username=user, password=password,
                                      tenant_name=tenant, auth_url=ep)

    def authenticate_keystone_user(self, keystone, user, password, tenant):
        """Authenticates a regular user with the keystone public endpoint."""
        self.log.debug('Authenticating keystone user ({})...'.format(user))
        ep = keystone.service_catalog.url_for(service_type='identity',
                                              endpoint_type='publicURL')
        return keystone_client.Client(username=user, password=password,
                                      tenant_name=tenant, auth_url=ep)

    def authenticate_glance_admin(self, keystone):
        """Authenticates admin user with glance."""
        self.log.debug('Authenticating glance admin...')
        ep = keystone.service_catalog.url_for(service_type='image',
                                              endpoint_type='adminURL')
        return glance_client.Client(ep, token=keystone.auth_token)

    def authenticate_heat_admin(self, keystone):
        """Authenticates the admin user with heat."""
        self.log.debug('Authenticating heat admin...')
        ep = keystone.service_catalog.url_for(service_type='orchestration',
                                              endpoint_type='publicURL')
        return heat_client.Client(endpoint=ep, token=keystone.auth_token)

    def authenticate_nova_user(self, keystone, user, password, tenant):
        """Authenticates a regular user with nova-api."""
        self.log.debug('Authenticating nova user ({})...'.format(user))
        ep = keystone.service_catalog.url_for(service_type='identity',
                                              endpoint_type='publicURL')
        return nova_client.Client(username=user, api_key=password,
                                  project_id=tenant, auth_url=ep)

    def create_cirros_image(self, glance, image_name):
        """Download the latest cirros image and upload it to glance."""
        self.log.debug('Creating glance image ({})...'.format(image_name))
        http_proxy = os.getenv('AMULET_HTTP_PROXY')
        self.log.debug('AMULET_HTTP_PROXY: {}'.format(http_proxy))
        if http_proxy:
            proxies = {'http': http_proxy}
            opener = urllib.FancyURLopener(proxies)
        else:
            opener = urllib.FancyURLopener()

        f = opener.open("http://download.cirros-cloud.net/version/released")
        version = f.read().strip()
        cirros_img = "cirros-{}-x86_64-disk.img".format(version)
        local_path = os.path.join('tests', cirros_img)

        if not os.path.exists(local_path):
            cirros_url = "http://{}/{}/{}".format("download.cirros-cloud.net",
                                                  version, cirros_img)
            opener.retrieve(cirros_url, local_path)
        f.close()

        with open(local_path) as f:
            image = glance.images.create(name=image_name, is_public=True,
                                         disk_format='qcow2',
                                         container_format='bare', data=f)
        count = 1
        status = image.status
        while status != 'active' and count < 10:
            time.sleep(3)
            image = glance.images.get(image.id)
            status = image.status
            self.log.debug('image status: {}'.format(status))
            count += 1

        if status != 'active':
            self.log.error('image creation timed out')
            return None

        return image

    def delete_image(self, glance, image):
        """Delete the specified image."""

        # /!\ DEPRECATION WARNING
        self.log.warn('/!\\ DEPRECATION WARNING:  use '
                      'delete_thing instead of delete_image.')
        self.log.debug('Deleting glance image ({})...'.format(image))
        num_before = len(list(glance.images.list()))
        glance.images.delete(image)

        count = 1
        num_after = len(list(glance.images.list()))
        while num_after != (num_before - 1) and count < 10:
            time.sleep(3)
            num_after = len(list(glance.images.list()))
            self.log.debug('number of images: {}'.format(num_after))
            count += 1

        if num_after != (num_before - 1):
            self.log.error('image deletion timed out')
            return False

        return True

    def create_instance(self, nova, image_name, instance_name, flavor):
        """Create the specified instance."""
        self.log.debug('Creating instance '
                       '({}|{}|{})'.format(instance_name, image_name, flavor))
        image = nova.images.find(name=image_name)
        flavor = nova.flavors.find(name=flavor)
        instance = nova.servers.create(name=instance_name, image=image,
                                       flavor=flavor)

        count = 1
        status = instance.status
        while status != 'ACTIVE' and count < 60:
            time.sleep(3)
            instance = nova.servers.get(instance.id)
            status = instance.status
            self.log.debug('instance status: {}'.format(status))
            count += 1

        if status != 'ACTIVE':
            self.log.error('instance creation timed out')
            return None

        return instance

    def delete_instance(self, nova, instance):
        """Delete the specified instance."""

        # /!\ DEPRECATION WARNING
        self.log.warn('/!\\ DEPRECATION WARNING:  use '
                      'delete_thing instead of delete_instance.')
        self.log.debug('Deleting instance ({})...'.format(instance))
        num_before = len(list(nova.servers.list()))
        nova.servers.delete(instance)

        count = 1
        num_after = len(list(nova.servers.list()))
        while num_after != (num_before - 1) and count < 10:
            time.sleep(3)
            num_after = len(list(nova.servers.list()))
            self.log.debug('number of instances: {}'.format(num_after))
            count += 1

        if num_after != (num_before - 1):
            self.log.error('instance deletion timed out')
            return False

        return True

    # NOTE(beisner):
    # Rather than having a delete_XYZ method for each of the numerous
    # openstack types/objects/things, use delete_thing and pass a pointer.
    #
    # Similarly, instead of having wait/check/timeout/confirm loops
    # built into numerous methods, use thing_reaches_status + a pointer.
    #
    # Not an homage to Dr. Seuss.  "Thing" is used due to conflict with
    # other more suitable names such as instance or object, both of
    # which may be confused with nova instance or swift object rather than a
    # python object or instance.  See heat amulet test for usage examples.

    def delete_thing(self, thing, thing_id, msg="thing", max_wait=120):
        """Delete one openstack object/thing, such as one instance, keypair,
        image, volume, stack, etc., and confirm deletion within max wait time.

        :param thing: pointer to openstack object type, ex:glance_client.images
        :param thing_id: unique name or id for the openstack object/thing
        :param msg: text to identify purpose in logging
        :param max_wait: maximum wait time in seconds
        :returns: True if successful, otherwise False
        """
        num_before = len(list(thing.list()))
        thing.delete(thing_id)

        tries = 0
        num_after = len(list(thing.list()))
        while num_after != (num_before - 1) and tries < (max_wait/4):
            self.log.debug('{} delete check: '
                           '{} [{}:{}] {}'.format(msg, tries,
                                                  num_before,
                                                  num_after,
                                                  thing_id))
            time.sleep(4)
            num_after = len(list(thing.list()))
            tries += 1

        self.log.debug('{}:  expected, actual count = {}, '
                       '{}'.format(msg, num_before - 1, num_after))

        if num_after == (num_before - 1):
            return True
        else:
            self.log.error('{} delete timed out'.format(msg))
            return False

    def thing_reaches_status(self, thing, thing_id, expected_stat='available',
                             msg='thing', max_wait=120):
        """Wait for an openstack object/thing's status to reach an
           expected status within a specified time.  Useful to confirm that
           nova instances, cinder vols, snapshots, glance images, heat stacks
           and other objects/things eventually reach the expected status.

        :param thing: pointer to openstack object type, ex: heat_client.stacks
        :param thing_id: unique id for the openstack object/thing
        :param expected_stat: status to expect object/thing to reach
        :param msg: text to identify purpose in logging
        :param max_wait: maximum wait time in seconds
        :returns: True if successful, False if status is not reached
        """

        tries = 0
        thing_stat = thing.get(thing_id).status
        while thing_stat != expected_stat and tries < (max_wait/4):
            self.log.debug('{} status check: '
                           '{} [{}:{}] {}'.format(msg, tries,
                                                  thing_stat,
                                                  expected_stat,
                                                  thing_id))
            sleep(4)
            thing_stat = thing.get(thing_id).status
            tries += 1

        self.log.debug('{}:  expected, actual status = {}, '
                       '{}'.format(msg, thing_stat, expected_stat))

        if thing_stat == expected_stat:
            return True
        else:
            self.log.debug('{} never reached expected status: '
                           '{}'.format(thing_id, expected_stat))
            return False
