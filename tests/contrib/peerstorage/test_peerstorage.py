from tests.helpers import FakeRelation
from testtools import TestCase
from mock import patch
from charmhelpers.contrib import peerstorage


TO_PATCH = ['relation_ids', 'relation_set', 'relation_get', 'local_unit']
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
