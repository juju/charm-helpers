from tests.helpers import FakeRelation
from testtools import TestCase
from mock import patch, call
from charmhelpers.contrib import peerstorage


TO_PATCH = [
    'current_relation_id',
    'is_relation_made',
    'local_unit',
    'relation_get',
    'relation_ids',
    'relation_set',
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
        peerstorage.peer_echo()
        self.relation_set.assert_called_with(relation_settings={'key1': 'value1',
                                                                'key2': 'value2'})

    def test_peer_echo_includes(self):
        peerstorage.peer_echo(['key1'])
        self.relation_set.assert_called_with(relation_settings={'key1': 'value1'})

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
