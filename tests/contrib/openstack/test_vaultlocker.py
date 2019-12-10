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
import sys
import unittest

import charmhelpers.contrib.openstack.vaultlocker as vaultlocker

from .test_os_contexts import TestDB


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
            'test-service/0_token':
                json.dumps('00c9a9ab-c523-459d-a250-2ce8f0877c03'),
        }
    }
}

DIRTY_RELATION = {
    'secrets-storage:1': {
        'vault/0': {
            'vault_url': json.dumps('http://vault:8200'),
            'test-service/0_role_id': json.dumps('test-role-from-vault'),
            'test-service/0_token':
                json.dumps('00c9a9ab-c523-459d-a250-2ce8f0877c03'),
        },
        'vault/1': {
            'vault_url': json.dumps('http://vault:8200'),
            'test-service/0_role_id': json.dumps('test-role-from-vault'),
            'test-service/0_token':
                json.dumps('67b36149-dc86-4b80-96c4-35b91847d16e'),
        }
    }
}

COMPLETE_WITH_CA_RELATION = {
    'secrets-storage:1': {
        'vault/0': {
            'vault_url': json.dumps('http://vault:8200'),
            'test-service/0_role_id': json.dumps('test-role-from-vault'),
            'test-service/0_token':
                json.dumps('00c9a9ab-c523-459d-a250-2ce8f0877c03'),
            'vault_ca': json.dumps('test-ca-data'),
        }
    }
}


class VaultLockerTestCase(unittest.TestCase):

    to_patch = [
        'hookenv',
        'templating',
        'alternatives',
        'host',
        'unitdata',
    ]

    _target_path = '/var/lib/charm/test-service/vaultlocker.conf'

    def setUp(self):
        for m in self.to_patch:
            setattr(self, m, self._patch(m))
        self.hookenv.service_name.return_value = 'test-service'
        self.hookenv.local_unit.return_value = 'test-service/0'
        self.db = TestDB()
        self.unitdata.kv.return_value = self.db
        fake_exc = mock.MagicMock()
        fake_exc.InvalidRequest = Exception
        self.fake_hvac = mock.MagicMock()
        self.fake_hvac.exceptions = fake_exc
        sys.modules['hvac'] = self.fake_hvac

    def fake_retrieve_secret_id(self, url=None, token=None):
        if token == self.good_token:
            return '31be8e65-20a3-45e0-a4a8-4d5a0554fb60'
        else:
            raise self.fake_hvac.exceptions.InvalidRequest

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
            lambda unit, rid:
                relation[rid][unit]
        )

    def test_context_incomplete(self):
        self._setup_relation(INCOMPLETE_RELATION)
        context = vaultlocker.VaultKVContext('charm-test')
        self.assertEqual(context(), {})
        self.hookenv.relation_ids.assert_called_with('secrets-storage')
        self.assertFalse(vaultlocker.vault_relation_complete())

    @mock.patch.object(vaultlocker, 'retrieve_secret_id')
    def test_context_complete(self, retrieve_secret_id):
        self._setup_relation(COMPLETE_RELATION)
        context = vaultlocker.VaultKVContext('charm-test')
        retrieve_secret_id.return_value = 'a3551c8d-0147-4cb6-afc6-efb3db2fccb2'
        self.assertEqual(context(),
                         {'role_id': 'test-role-from-vault',
                          'secret_backend': 'charm-test',
                          'secret_id': 'a3551c8d-0147-4cb6-afc6-efb3db2fccb2',
                          'vault_url': 'http://vault:8200'})
        self.hookenv.relation_ids.assert_called_with('secrets-storage')
        self.assertTrue(vaultlocker.vault_relation_complete())
        calls = [mock.call(url='http://vault:8200',
                           token='00c9a9ab-c523-459d-a250-2ce8f0877c03')]
        retrieve_secret_id.assert_has_calls(calls)

    @mock.patch.object(vaultlocker, 'retrieve_secret_id')
    def test_context_complete_cached_secret_id(self, retrieve_secret_id):
        self._setup_relation(COMPLETE_RELATION)
        context = vaultlocker.VaultKVContext('charm-test')
        self.db.set('secret-id', '5502fd27-059b-4b0a-91b2-eaff40b6a112')
        self.good_token = 'invalid-token'  # i.e. cause failure
        retrieve_secret_id.side_effect = self.fake_retrieve_secret_id
        self.assertEqual(context(),
                         {'role_id': 'test-role-from-vault',
                          'secret_backend': 'charm-test',
                          'secret_id': '5502fd27-059b-4b0a-91b2-eaff40b6a112',
                          'vault_url': 'http://vault:8200'})
        self.hookenv.relation_ids.assert_called_with('secrets-storage')
        self.assertTrue(vaultlocker.vault_relation_complete())
        calls = [mock.call(url='http://vault:8200',
                           token='00c9a9ab-c523-459d-a250-2ce8f0877c03')]
        retrieve_secret_id.assert_has_calls(calls)

    @mock.patch.object(vaultlocker, 'retrieve_secret_id')
    def test_purge_old_tokens(self, retrieve_secret_id):
        self._setup_relation(DIRTY_RELATION)
        context = vaultlocker.VaultKVContext('charm-test')
        self.db.set('secret-id', '5502fd27-059b-4b0a-91b2-eaff40b6a112')
        self.good_token = '67b36149-dc86-4b80-96c4-35b91847d16e'
        retrieve_secret_id.side_effect = self.fake_retrieve_secret_id
        self.assertEqual(context(),
                         {'role_id': 'test-role-from-vault',
                          'secret_backend': 'charm-test',
                          'secret_id': '31be8e65-20a3-45e0-a4a8-4d5a0554fb60',
                          'vault_url': 'http://vault:8200'})
        self.hookenv.relation_ids.assert_called_with('secrets-storage')
        self.assertTrue(vaultlocker.vault_relation_complete())
        self.assertEquals(self.db.get('secret-id'),
                          '31be8e65-20a3-45e0-a4a8-4d5a0554fb60')
        calls = [mock.call(url='http://vault:8200',
                           token='67b36149-dc86-4b80-96c4-35b91847d16e')]
        retrieve_secret_id.assert_has_calls(calls)

    @mock.patch.object(vaultlocker, 'retrieve_secret_id')
    def test_context_complete_cached_dirty_data(self, retrieve_secret_id):
        self._setup_relation(DIRTY_RELATION)
        context = vaultlocker.VaultKVContext('charm-test')
        self.db.set('secret-id', '5502fd27-059b-4b0a-91b2-eaff40b6a112')
        self.good_token = '67b36149-dc86-4b80-96c4-35b91847d16e'
        retrieve_secret_id.side_effect = self.fake_retrieve_secret_id
        self.assertEqual(context(),
                         {'role_id': 'test-role-from-vault',
                          'secret_backend': 'charm-test',
                          'secret_id': '31be8e65-20a3-45e0-a4a8-4d5a0554fb60',
                          'vault_url': 'http://vault:8200'})
        self.hookenv.relation_ids.assert_called_with('secrets-storage')
        self.assertTrue(vaultlocker.vault_relation_complete())
        self.assertEquals(self.db.get('secret-id'),
                          '31be8e65-20a3-45e0-a4a8-4d5a0554fb60')
        calls = [mock.call(url='http://vault:8200',
                           token='67b36149-dc86-4b80-96c4-35b91847d16e')]
        retrieve_secret_id.assert_has_calls(calls)

    @mock.patch.object(vaultlocker, 'retrieve_secret_id')
    def test_context_complete_with_ca(self, retrieve_secret_id):
        self._setup_relation(COMPLETE_WITH_CA_RELATION)
        retrieve_secret_id.return_value = 'token1234'
        context = vaultlocker.VaultKVContext('charm-test')
        retrieve_secret_id.return_value = 'a3551c8d-0147-4cb6-afc6-efb3db2fccb2'
        self.assertEqual(context(),
                         {'role_id': 'test-role-from-vault',
                          'secret_backend': 'charm-test',
                          'secret_id': 'a3551c8d-0147-4cb6-afc6-efb3db2fccb2',
                          'vault_url': 'http://vault:8200',
                          'vault_ca': 'test-ca-data'})
        self.hookenv.relation_ids.assert_called_with('secrets-storage')
        self.assertTrue(vaultlocker.vault_relation_complete())
        calls = [mock.call(url='http://vault:8200',
                           token='00c9a9ab-c523-459d-a250-2ce8f0877c03')]
        retrieve_secret_id.assert_has_calls(calls)
