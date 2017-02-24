#!/usr/bin/python
#
# Copyright 2017 Canonical Ltd
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import six
from charmhelpers.fetch import apt_install, apt_update


def get_keystone_manager(endpoint, token, api_version):
    """Return a keystonemanager for the correct API version

    @param endpoint: the keystone endpoint to point client at
    @param token: the keystone token
    @param api_version: version of the keystone api the client should use
    @returns keystonemanager class used for interrogating keystone
    """
    if api_version == 2:
        return KeystoneManager2(endpoint, token)
    if api_version == 3:
        return KeystoneManager3(endpoint, token)
    raise ValueError('No manager found for api version {}'.format(api_version))


class KeystoneManager(object):

    def resolve_service_id(self, name, service_type=None):
        """Find the service_id of a given service"""
        services = [s._info for s in self.api.services.list()]

        for s in services:
            if service_type:
                if (name.lower() == s['name'].lower() and
                        service_type == s['type']):
                    return s['id']
            else:
                if name.lower() == s['name'].lower():
                    return s['id']
        return None

    def service_exists(self, service_name, service_type=None):
        """Determine if the given service exists on the service list"""
        return self.resolve_service_id(service_name, service_type) is not None


class KeystoneManager2(KeystoneManager):

    def __init__(self, endpoint, token):
        try:
            from keystoneclient.v2_0 import client
        except ImportError:
            apt_update(fatal=True)
            if six.PY2:
                apt_install('python-keystoneclient', fatal=True)
            else:
                apt_install('python3-keystoneclient', fatal=True)

            from keystoneclient.v2_0 import client

        self.api_version = 2
        self.api = client.Client(endpoint=endpoint, token=token)


class KeystoneManager3(KeystoneManager):

    def __init__(self, endpoint, token):
        try:
            from keystoneclient.v3 import client as keystoneclient_v3
            from keystoneclient.auth import token_endpoint
            from keystoneclient import session
        except ImportError:
            apt_update(fatal=True)
            if six.PY2:
                apt_install('python-keystoneclient', fatal=True)
            else:
                apt_install('python3-keystoneclient', fatal=True)

            from keystoneclient.v3 import client as keystoneclient_v3
            from keystoneclient.auth import token_endpoint
            from keystoneclient import session

        self.api_version = 3
        keystone_auth_v3 = token_endpoint.Token(endpoint=endpoint, token=token)
        keystone_session_v3 = session.Session(auth=keystone_auth_v3)
        self.api = keystoneclient_v3.Client(session=keystone_session_v3)
