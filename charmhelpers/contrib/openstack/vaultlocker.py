# Copyright 2018 Canonical Limited.
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

import json
import os

import charmhelpers.contrib.openstack.alternatives as alternatives
import charmhelpers.contrib.openstack.context as context

import charmhelpers.core.hookenv as hookenv
import charmhelpers.core.host as host
import charmhelpers.core.templating as templating

VAULTLOCKER_BACKEND = 'charm-vaultlocker'


class VaultKVContext(context.OSContextGenerator):
    """Vault KV context for interaction with vault-kv interfaces"""
    interfaces = ['secrets-storage']

    def __init__(self, secret_backend=None):
        super(context.OSContextGenerator, self).__init__()
        self.secret_backend = (
            secret_backend or 'charm-{}'.format(hookenv.service_name())
        )

    def __call__(self):
        for relation_id in hookenv.relation_ids(self.interfaces[0]):
            for unit in hookenv.related_units(relation_id):
                vault_url = hookenv.relation_get(
                    'vault_url',
                    unit=unit,
                    rid=relation_id
                )
                role_id = hookenv.relation_get(
                    '{}_role_id'.format(hookenv.local_unit()),
                    unit=unit,
                    rid=relation_id
                )

                if vault_url and role_id:
                    ctxt = {
                        'vault_url': json.loads(vault_url),
                        'role_id': json.loads(role_id),
                        'secret_backend': self.secret_backend,
                    }
                    vault_ca = hookenv.relation_get(
                        'vault_ca',
                        unit=unit,
                        rid=relation_id
                    )
                    if vault_ca:
                        ctxt['vault_ca'] = json.loads(vault_ca)
                    self.complete = True
                    return ctxt
        return {}


def write_vaultlocker_conf(context, priority=100):
    """Write vaultlocker configuration to disk and install alternative

    :param context: Dict of data from vault-kv relation
    :ptype: context: dict
    :param priority: Priority of alternative configuration
    :ptype: priority: int"""
    charm_vl_path = "/var/lib/charm/{}/vaultlocker.conf".format(
        hookenv.service_name()
    )
    host.mkdir(os.path.dirname(charm_vl_path), perms=0o700)
    templating.render(source='vaultlocker.conf.j2',
                      target=charm_vl_path,
                      context=context, perms=0o600),
    alternatives.install_alternative('vaultlocker.conf',
                                     '/etc/vaultlocker/vaultlocker.conf',
                                     charm_vl_path, priority)


def vault_relation_complete(backend=None):
    """Determine whether vault relation is complete

    :param backend: Name of secrets backend requested
    :ptype backend: string
    :returns: whether the relation to vault is complete
    :rtype: bool"""
    vault_kv = VaultKVContext(secret_backend=backend or VAULTLOCKER_BACKEND)
    vault_kv()
    return vault_kv.complete
