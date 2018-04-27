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
import mock
import os
import unittest

import charmhelpers.contrib.openstack.vaultlocker as vaultlocker


INCOMPLETE_RELATION = {
    'secrets-storage:1': {
        'vault/0': {}
    }
}

COMPLETE_RELATION = {
    'secrets-storage:1': {
        'vault/0': {
            'vault_url': json.dumps('http://vault:8200'),
            'test-service/0_role_id': json.dumps('test-role-from-vault'),
        }
    }
}

COMPLETE_WITH_CA_RELATION = {
    'secrets-storage:1': {
        'vault/0': {
            'vault_url': json.dumps('http://vault:8200'),
            'test-service/0_role_id': json.dumps('test-role-from-vault'),
            'vault_ca': json.dumps('test-ca-data'),
        }
    }
}


class VaultLockerTestCase(unittest.TestCase):

    to_patch = [
        'hookenv',
        'templating',
        'alternatives',
        'host'
    ]

    _target_path = '/var/lib/charm/test-service/vaultlocker.conf'

    def setUp(self):
        for m in self.to_patch:
            setattr(self, m, self._patch(m))
        self.hookenv.service_name.return_value = 'test-service'
        self.hookenv.local_unit.return_value = 'test-service/0'

    def _patch(self, target):
        _m = mock.patch.object(vaultlocker, target)
        _mock = _m.start()
        self.addCleanup(_m.stop)
        return _mock

    def test_write_vl_config(self):
        ctxt = {'test': 'data'}
        vaultlocker.write_vaultlocker_conf(context=ctxt)
        self.hookenv.service_name.assert_called_once_with()
        self.host.mkdir.assert_called_once_with(
            os.path.dirname(self._target_path),
            perms=0o700
        )
        self.templating.render.assert_called_once_with(
            source='vaultlocker.conf.j2',
            target=self._target_path,
            context=ctxt,
            perms=0o600,
        )
        self.alternatives.install_alternative.assert_called_once_with(
            'vaultlocker.conf',
            '/etc/vaultlocker/vaultlocker.conf',
            self._target_path,
            100
        )

    def test_write_vl_config_priority(self):
        ctxt = {'test': 'data'}
        vaultlocker.write_vaultlocker_conf(context=ctxt, priority=200)
        self.hookenv.service_name.assert_called_once_with()
        self.host.mkdir.assert_called_once_with(
            os.path.dirname(self._target_path),
            perms=0o700
        )
        self.templating.render.assert_called_once_with(
            source='vaultlocker.conf.j2',
            target=self._target_path,
            context=ctxt,
            perms=0o600,
        )
        self.alternatives.install_alternative.assert_called_once_with(
            'vaultlocker.conf',
            '/etc/vaultlocker/vaultlocker.conf',
            self._target_path,
            200
        )

    def _setup_relation(self, relation):
        self.hookenv.relation_ids.side_effect = (
            lambda _: relation.keys()
        )
        self.hookenv.related_units.side_effect = (
            lambda rid: relation[rid].keys()
        )
        self.hookenv.relation_get.side_effect = (
            lambda attribute, unit, rid:
                relation[rid][unit].get(attribute)
        )

    def test_context_incomplete(self):
        self._setup_relation(INCOMPLETE_RELATION)
        context = vaultlocker.VaultKVContext('charm-test')
        self.assertEqual(context(), {})
        self.hookenv.relation_ids.assert_called_with('secrets-storage')
        self.assertFalse(vaultlocker.vault_relation_complete())

    def test_context_complete(self):
        self._setup_relation(COMPLETE_RELATION)
        context = vaultlocker.VaultKVContext('charm-test')
        self.assertEqual(context(),
                         {'role_id': 'test-role-from-vault',
                          'secret_backend': 'charm-test',
                          'vault_url': 'http://vault:8200'})
        self.hookenv.relation_ids.assert_called_with('secrets-storage')
        self.assertTrue(vaultlocker.vault_relation_complete())

    def test_context_complete_with_ca(self):
        self._setup_relation(COMPLETE_WITH_CA_RELATION)
        context = vaultlocker.VaultKVContext('charm-test')
        self.assertEqual(context(),
                         {'role_id': 'test-role-from-vault',
                          'secret_backend': 'charm-test',
                          'vault_url': 'http://vault:8200',
                          'vault_ca': 'test-ca-data'})
        self.hookenv.relation_ids.assert_called_with('secrets-storage')
        self.assertTrue(vaultlocker.vault_relation_complete())
