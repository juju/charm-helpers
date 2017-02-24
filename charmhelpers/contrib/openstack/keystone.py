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


def get_api_suffix(api_version):
    """Return the formatted api suffix for the given version
    @param api_version: version of the keystone endpoint
    @returns the api suffix formatted according to the given api
    version
    """
    return 'v2.0' if api_version == 2 else 'v3'


def format_endpoint(schema, addr, port, api_version):
    """Return a formatted keystone endpoint
    @param schema: http or https
    @param addr: ipv4/ipv6 host of the keystone service
    @param port: port of the keystone service
    @param api_version: 2 or 3
    @returns a fully formatted keystone endpoint
    """
    return '{}://{}:{}/{}/'.format(schema, addr, port,
                                   get_api_suffix(api_version))


def get_keystone_manager(endpoint, api_version, **kwargs):
    """Return a keystonemanager for the correct API version

    @param endpoint: the keystone endpoint to point client at
    @param token: the keystone token
    @param api_version: version of the keystone api the client should use
    @returns keystonemanager class used for interrogating keystone
    """
    if api_version == 2:
        return KeystoneManager2(endpoint, **kwargs)
    if api_version == 3:
        return KeystoneManager3(endpoint, **kwargs)
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

    def __init__(self, endpoint, **kwargs):
        try:
            from keystoneclient.v2_0 import client
            from keystoneauth1.identity import v2
            from keystoneauth1 import session
        except ImportError:
            if six.PY2:
                apt_install(["python-keystoneclient",
                             "python-keystoneauth1"],
                            fatal=True)
            else:
                apt_install(["python3-keystoneclient",
                             "python3-keystoneauth1"],
                            fatal=True)

            from keystoneclient.v2_0 import client
            from keystoneauth1.identity import v2
            from keystoneauth1 import session

        self.api_version = 2

        token = kwargs.get("token", None)
        if token:
            auth = v2.Token(auth_url=endpoint, token=token)
            sess = session.Session(auth=auth)
        else:
            auth = v2.Password(username=kwargs.get("username"),
                               password=kwargs.get("password"),
                               tenant_name=kwargs.get("tenant_name"),
                               auth_url=endpoint)
            sess = session.Session(auth=auth)

        self.api = client.Client(session=sess)


class KeystoneManager3(KeystoneManager):

    def __init__(self, endpoint, **kwargs):
        try:
            from keystoneclient.v3 import client
            from keystoneclient.auth import token_endpoint
            from keystoneclient import session
        except ImportError:
            if six.PY2:
                apt_install(["python-keystoneclient",
                             "python-keystoneauth1"],
                            fatal=True)
            else:
                apt_install(["python3-keystoneclient",
                             "python3-keystoneauth1"],
                            fatal=True)

            from keystoneclient.v3 import client
            from keystoneclient.auth import token_endpoint
            from keystoneclient import session
            from keystoneauth1.identity import v3

        self.api_version = 3

        token = kwargs.get("token", None)
        if token:
            auth = token_endpoint.Token(endpoint=endpoint,
                                        token=token)
            sess = session.Session(auth=auth)
        else:
            auth = v3.Password(auth_url=endpoint,
                               user_id=kwargs.get("username"),
                               password=kwargs.get("password"),
                               project_id=kwargs.get("project_id"))
            sess = session.Session(auth=auth)

        self.api = client.Client(session=sess)
