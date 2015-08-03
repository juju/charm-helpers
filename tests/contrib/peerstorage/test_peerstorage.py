import copy
import json

from tests.helpers import FakeRelation
from testtools import TestCase
from mock import patch, call
from charmhelpers.contrib import peerstorage


TO_PATCH = [
    'current_relation_id',
    'is_relation_made',
    'local_unit',
    'relation_get',
    '_relation_get',
    'relation_ids',
    'relation_set',
    '_relation_set',
    '_leader_get',
    'leader_set',
    'is_leader',
]
FAKE_RELATION_NAME = 'cluster'
FAKE_RELATION = {
    'cluster:0': {
        'cluster/0': {
        },
        'cluster/1': {
        },
        'cluster/2': {
        },
    },

}
FAKE_RELATION_IDS = ['cluster:0']
FAKE_LOCAL_UNIT = 'test_host'


class TestPeerStorage(TestCase):
    def setUp(self):
        super(TestPeerStorage, self).setUp()
        for m in TO_PATCH:
            setattr(self, m, self._patch(m))
        self.fake_relation_name = FAKE_RELATION_NAME
        self.fake_relation = FakeRelation(FAKE_RELATION)
        self.local_unit.return_value = FAKE_LOCAL_UNIT
        self.relation_get.return_value = {'key1': 'value1',
                                          'key2': 'value2',
                                          'private-address': '127.0.0.1',
                                          'public-address': '91.189.90.159'}

    def _patch(self, method):
        _m = patch('charmhelpers.contrib.peerstorage.' + method)
        mock = _m.start()
        self.addCleanup(_m.stop)
        return mock

    def test_peer_retrieve_no_relation(self):
        self.relation_ids.return_value = []
        self.assertRaises(ValueError, peerstorage.peer_retrieve, 'key', relation_name=self.fake_relation_name)

    def test_peer_retrieve_with_relation(self):
        self.relation_ids.return_value = FAKE_RELATION_IDS
        peerstorage.peer_retrieve('key', self.fake_relation_name)
        self.relation_get.assert_called_with(attribute='key', rid=FAKE_RELATION_IDS[0], unit=FAKE_LOCAL_UNIT)

    def test_peer_store_no_relation(self):
        self.relation_ids.return_value = []
        self.assertRaises(ValueError, peerstorage.peer_store, 'key', 'value', relation_name=self.fake_relation_name)

    def test_peer_store_with_relation(self):
        self.relation_ids.return_value = FAKE_RELATION_IDS
        peerstorage.peer_store('key', 'value', self.fake_relation_name)
        self.relation_set.assert_called_with(relation_id=FAKE_RELATION_IDS[0],
                                             relation_settings={'key': 'value'})

    def test_peer_echo_no_includes(self):
        peerstorage.is_leader.side_effect = NotImplementedError
        settings = {'key1': 'value1', 'key2': 'value2'}
        self._relation_get.copy.return_value = settings
        self._relation_get.return_value = settings
        peerstorage.peer_echo()
        self._relation_set.assert_called_with(relation_settings=settings)

    def test_peer_echo_includes(self):
        peerstorage.is_leader.side_effect = NotImplementedError
        settings = {'key1': 'value1'}
        self._relation_get.copy.return_value = settings
        self._relation_get.return_value = settings
        peerstorage.peer_echo(['key1'])
        self._relation_set.assert_called_with(relation_settings=settings)

    @patch.object(peerstorage, 'peer_store')
    def test_peer_store_and_set_no_relation(self, peer_store):
        self.is_relation_made.return_value = False
        peerstorage.peer_store_and_set(relation_id='db', kwarg1='kwarg1_v')
        self.relation_set.assert_called_with(relation_id='db',
                                             relation_settings={},
                                             kwarg1='kwarg1_v')
        peer_store.assert_not_called()

    @patch.object(peerstorage, 'peer_store')
    def test_peer_store_and_set_no_relation_fatal(self, peer_store):
        self.is_relation_made.return_value = False
        self.assertRaises(ValueError,
                          peerstorage.peer_store_and_set,
                          relation_id='db',
                          kwarg1='kwarg1_v',
                          peer_store_fatal=True)

    @patch.object(peerstorage, 'peer_store')
    def test_peer_store_and_set_kwargs(self, peer_store):
        self.is_relation_made.return_value = True
        peerstorage.peer_store_and_set(relation_id='db', kwarg1='kwarg1_v')
        self.relation_set.assert_called_with(relation_id='db',
                                             relation_settings={},
                                             kwarg1='kwarg1_v')
        calls = [call('db_kwarg1', 'kwarg1_v', relation_name='cluster')]
        peer_store.assert_has_calls(calls, any_order=True)

    @patch.object(peerstorage, 'peer_store')
    def test_peer_store_and_rel_settings(self, peer_store):
        self.is_relation_made.return_value = True
        rel_setting = {
            'rel_set1': 'relset1_v'
        }
        peerstorage.peer_store_and_set(relation_id='db',
                                       relation_settings=rel_setting)
        self.relation_set.assert_called_with(relation_id='db',
                                             relation_settings=rel_setting)
        calls = [call('db_rel_set1', 'relset1_v', relation_name='cluster')]
        peer_store.assert_has_calls(calls, any_order=True)

    @patch.object(peerstorage, 'peer_store')
    def test_peer_store_and_set(self, peer_store):
        self.is_relation_made.return_value = True
        rel_setting = {
            'rel_set1': 'relset1_v'
        }
        peerstorage.peer_store_and_set(relation_id='db',
                                       relation_settings=rel_setting,
                                       kwarg1='kwarg1_v',
                                       delimiter='+')
        self.relation_set.assert_called_with(relation_id='db',
                                             relation_settings=rel_setting,
                                             kwarg1='kwarg1_v')
        calls = [call('db+rel_set1', 'relset1_v', relation_name='cluster'),
                 call('db+kwarg1', 'kwarg1_v', relation_name='cluster')]
        peer_store.assert_has_calls(calls, any_order=True)

    @patch.object(peerstorage, 'peer_retrieve')
    def test_peer_retrieve_by_prefix(self, peer_retrieve):
        rel_id = 'db:2'
        settings = {
            'user': 'bob',
            'pass': 'reallyhardpassword',
            'host': 'myhost',
        }
        peer_settings = {rel_id + '_' + k: v for k, v in settings.items()}
        peer_retrieve.return_value = peer_settings
        self.assertEquals(peerstorage.peer_retrieve_by_prefix(rel_id), settings)

    @patch.object(peerstorage, 'peer_retrieve')
    def test_peer_retrieve_by_prefix_empty_relation(self, peer_retrieve):
        # If relation-get returns None, peer_retrieve_by_prefix returns
        # an empty dictionary.
        peer_retrieve.return_value = None
        rel_id = 'db:2'
        self.assertEquals(peerstorage.peer_retrieve_by_prefix(rel_id), {})

    @patch.object(peerstorage, 'peer_retrieve')
    def test_peer_retrieve_by_prefix_exc_list(self, peer_retrieve):
        rel_id = 'db:2'
        settings = {
            'user': 'bob',
            'pass': 'reallyhardpassword',
            'host': 'myhost',
        }
        peer_settings = {rel_id + '_' + k: v for k, v in settings.items()}
        del settings['host']
        peer_retrieve.return_value = peer_settings
        self.assertEquals(peerstorage.peer_retrieve_by_prefix(rel_id,
                                                              exc_list=['host']),
                          settings)

    @patch.object(peerstorage, 'peer_retrieve')
    def test_peer_retrieve_by_prefix_inc_list(self, peer_retrieve):
        rel_id = 'db:2'
        settings = {
            'user': 'bob',
            'pass': 'reallyhardpassword',
            'host': 'myhost',
        }
        peer_settings = {rel_id + '_' + k: v for k, v in settings.items()}
        peer_retrieve.return_value = peer_settings
        self.assertEquals(peerstorage.peer_retrieve_by_prefix(rel_id,
                                                              inc_list=['host']),
                          {'host': 'myhost'})

    def test_leader_get_migration_is_leader(self):
        self.is_leader.return_value = True
        l_settings = {'s3': 3}
        r_settings = {'s1': 1, 's2': 2}

        def mock_relation_get(attribute=None, unit=None, rid=None):
            if attribute:
                if attribute in r_settings:
                    return r_settings.get(attribute)
                else:
                    return None

            return copy.deepcopy(r_settings)

        def mock_leader_get(attribute=None):
            if attribute:
                if attribute in l_settings:
                    return l_settings.get(attribute)
                else:
                    return None

            return copy.deepcopy(l_settings)

        def mock_leader_set(settings=None, **kwargs):
            if settings:
                l_settings.update(settings)

            l_settings.update(kwargs)

        def check_leader_db(dicta, dictb):
            _dicta = copy.deepcopy(dicta)
            _dictb = copy.deepcopy(dictb)
            miga = json.loads(_dicta[migration_key]).sort()
            migb = json.loads(_dictb[migration_key]).sort()
            self.assertEqual(miga, migb)
            del _dicta[migration_key]
            del _dictb[migration_key]
            self.assertEqual(_dicta, _dictb)

        migration_key = '__leader_get_migrated_settings__'
        self._relation_get.side_effect = mock_relation_get
        self._leader_get.side_effect = mock_leader_get
        self.leader_set.side_effect = mock_leader_set

        self.assertEqual({'s1': 1, 's2': 2}, peerstorage._relation_get())
        self.assertEqual({'s3': 3}, peerstorage._leader_get())
        self.assertEqual({'s1': 1, 's2': 2, 's3': 3}, peerstorage.leader_get())
        check_leader_db({'s1': 1, 's2': 2, 's3': 3,
                         migration_key: '["s2", "s1"]'}, l_settings)
        self.assertTrue(peerstorage.leader_set.called)

        peerstorage.leader_set.reset_mock()
        self.assertEqual({'s1': 1, 's2': 2, 's3': 3}, peerstorage.leader_get())
        check_leader_db({'s1': 1, 's2': 2, 's3': 3,
                         migration_key: '["s2", "s1"]'}, l_settings)
        self.assertFalse(peerstorage.leader_set.called)

        l_settings = {'s3': 3}
        peerstorage.leader_set.reset_mock()
        self.assertEqual(1, peerstorage.leader_get('s1'))
        check_leader_db({'s1': 1, 's3': 3,
                         migration_key: '["s1"]'}, l_settings)
        self.assertTrue(peerstorage.leader_set.called)

        # Test that leader vals take precedence over non-leader vals
        r_settings['s3'] = 2
        r_settings['s4'] = 3
        l_settings['s4'] = 4

        peerstorage.leader_set.reset_mock()
        self.assertEqual(4, peerstorage.leader_get('s4'))
        check_leader_db({'s1': 1, 's3': 3, 's4': 4,
                         migration_key: '["s1", "s4"]'}, l_settings)
        self.assertTrue(peerstorage.leader_set.called)

        peerstorage.leader_set.reset_mock()
        self.assertEqual({'s1': 1, 's2': 2, 's3': 2, 's4': 3},
                         peerstorage._relation_get())
        check_leader_db({'s1': 1, 's3': 3, 's4': 4,
                         migration_key: '["s1", "s4"]'},
                        peerstorage._leader_get())
        self.assertEqual({'s1': 1, 's2': 2, 's3': 3, 's4': 4},
                         peerstorage.leader_get())
        check_leader_db({'s1': 1, 's2': 2, 's3': 3, 's4': 4,
                         migration_key: '["s3", "s2", "s1", "s4"]'},
                        l_settings)
        self.assertTrue(peerstorage.leader_set.called)

    def test_leader_get_migration_is_not_leader(self):
        self.is_leader.return_value = False
        l_settings = {'s3': 3}
        r_settings = {'s1': 1, 's2': 2}

        def mock_relation_get(attribute=None, unit=None, rid=None):
            if attribute:
                if attribute in r_settings:
                    return r_settings.get(attribute)
                else:
                    return None

            return copy.deepcopy(r_settings)

        def mock_leader_get(attribute=None):
            if attribute:
                if attribute in l_settings:
                    return l_settings.get(attribute)
                else:
                    return None

            return copy.deepcopy(l_settings)

        def mock_leader_set(settings=None, **kwargs):
            if settings:
                l_settings.update(settings)

            l_settings.update(kwargs)

        self._relation_get.side_effect = mock_relation_get
        self._leader_get.side_effect = mock_leader_get
        self.leader_set.side_effect = mock_leader_set
        self.assertEqual({'s1': 1, 's2': 2}, peerstorage._relation_get())
        self.assertEqual({'s3': 3}, peerstorage._leader_get())
        self.assertEqual({'s3': 3}, peerstorage.leader_get())
        self.assertEqual({'s3': 3}, l_settings)
        self.assertFalse(peerstorage.leader_set.called)

        self.assertEqual({'s3': 3}, peerstorage.leader_get())
        self.assertEqual({'s3': 3}, l_settings)
        self.assertFalse(peerstorage.leader_set.called)

        # Test that leader vals take precedence over non-leader vals
        r_settings['s3'] = 2
        r_settings['s4'] = 3
        l_settings['s4'] = 4

        self.assertEqual(4, peerstorage.leader_get('s4'))
        self.assertEqual({'s3': 3, 's4': 4}, l_settings)
        self.assertFalse(peerstorage.leader_set.called)
