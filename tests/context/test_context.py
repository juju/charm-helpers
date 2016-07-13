# Copyright 2014-2015 Canonical Limited.
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
import unittest
from mock import patch, sentinel
import six

from charmhelpers import context
from charmhelpers.core import hookenv


class TestRelations(unittest.TestCase):
    def setUp(self):
        def install(*args, **kw):
            p = patch.object(*args, **kw)
            p.start()
            self.addCleanup(p.stop)

        install(hookenv, 'relation_types', return_value=['rel', 'pear'])
        install(hookenv, 'peer_relation_id', return_value='pear:9')
        install(hookenv, 'relation_ids',
                side_effect=lambda x: ['{}:{}'.format(x, i)
                                       for i in range(9, 11)])
        install(hookenv, 'related_units',
                side_effect=lambda x: ['svc_' + x.replace(':', '/')])
        install(hookenv, 'local_unit', return_value='foo/1')
        install(hookenv, 'relation_get')
        install(hookenv, 'relation_set')
        # install(hookenv, 'is_leader', return_value=False)

    def test_relations(self):
        rels = context.Relations()
        self.assertListEqual(list(rels.keys()),
                             ['pear', 'rel'])  # Ordered alphabetically
        self.assertListEqual(list(rels['rel'].keys()),
                             ['rel:9', 'rel:10'])  # Ordered numerically

        # Relation data is loaded on demand, not on instantiation.
        self.assertFalse(hookenv.relation_get.called)

        # But we did have to retrieve some lists of units etc.
        self.assertGreaterEqual(hookenv.relation_ids.call_count, 2)
        self.assertGreaterEqual(hookenv.related_units.call_count, 2)

    def test_relations_peer(self):
        # The Relations instance has a short cut to the peer relation.
        # If the charm has managed to get multiple peer relations,
        # it returns the 'primary' one used here and returned by
        # hookenv.peer_relation_id()
        rels = context.Relations()
        self.assertIs(rels.peer, rels['pear']['pear:9'])

    def test_relation(self):
        rel = context.Relations()['rel']['rel:9']
        self.assertEqual(rel.relid, 'rel:9')
        self.assertEqual(rel.relname, 'rel')
        self.assertEqual(rel.service, 'svc_rel')
        self.assertTrue(isinstance(rel.local, context.RelationInfo))
        self.assertEqual(rel.local.unit, hookenv.local_unit())
        self.assertTrue(isinstance(rel.peers, context.OrderedDict))
        self.assertTrue(len(rel.peers), 2)
        self.assertTrue(isinstance(rel.peers['svc_pear/9'],
                                   context.RelationInfo))

        # I use this in my log messages. Relation id for identity
        # plus service name for ease of reference.
        self.assertEqual(str(rel), 'rel:9 (svc_rel)')

    def test_relation_no_peer_relation(self):
        hookenv.peer_relation_id.return_value = None
        rel = context.Relation('rel:10')
        self.assertTrue(rel.peers is None)

    def test_relation_no_peers(self):
        hookenv.related_units.side_effect = None
        hookenv.related_units.return_value = []
        rel = context.Relation('rel:10')
        self.assertDictEqual(rel.peers, {})

    def test_peer_relation(self):
        peer_rel = context.Relations().peer
        # The peer relation does not have a 'peers' properly. We
        # could give it one for symmetry, but it seems somewhat silly.
        self.assertTrue(peer_rel.peers is None)

    def test_relationinfo(self):
        hookenv.relation_get.return_value = {sentinel.key: 'value'}
        r = context.RelationInfo('rel:10', 'svc_rel/9')

        self.assertEqual(r.relname, 'rel')
        self.assertEqual(r.relid, 'rel:10')
        self.assertEqual(r.unit, 'svc_rel/9')
        self.assertEqual(r.service, 'svc_rel')
        self.assertEqual(r.number, 9)

        self.assertFalse(hookenv.relation_get.called)
        self.assertEqual(r[sentinel.key], 'value')
        hookenv.relation_get.assert_called_with(unit='svc_rel/9', rid='rel:10')

        # Updates fail
        with self.assertRaises(TypeError):
            r['newkey'] = 'foo'

        # Deletes fail
        with self.assertRaises(TypeError):
            del r[sentinel.key]

        # I use this for logging.
        self.assertEqual(str(r), 'rel:10 (svc_rel/9)')

    def test_relationinfo_local(self):
        r = context.RelationInfo('rel:10', hookenv.local_unit())

        # Updates work, with standard strings.
        r[sentinel.key] = 'value'
        hookenv.relation_set.assert_called_once_with(
            'rel:10', {sentinel.key: 'value'})

        # Python 2 unicode strings work too.
        hookenv.relation_set.reset_mock()
        r[sentinel.key] = six.u('value')
        hookenv.relation_set.assert_called_once_with(
            'rel:10', {sentinel.key: six.u('value')})

        # Byte strings fail under Python 3.
        if six.PY3:
            with self.assertRaises(ValueError):
                r[sentinel.key] = six.b('value')

        # Deletes work
        del r[sentinel.key]
        hookenv.relation_set.assert_called_with('rel:10', {sentinel.key: None})

        # Attempting to write a non-string fails
        with self.assertRaises(ValueError):
            r[sentinel.key] = 42


class TestLeader(unittest.TestCase):
    @patch.object(hookenv, 'leader_get')
    def test_get(self, leader_get):
        leader_get.return_value = {'a_key': 'a_value'}

        leader = context.Leader()
        self.assertEqual(leader['a_key'], 'a_value')
        leader_get.assert_called_with()

        with self.assertRaises(KeyError):
            leader['missing']

    @patch.object(hookenv, 'leader_set')
    @patch.object(hookenv, 'leader_get')
    @patch.object(hookenv, 'is_leader')
    def test_set(self, is_leader, leader_get, leader_set):
        is_leader.return_value = True
        leader = context.Leader()

        # Updates work
        leader[sentinel.key] = 'foo'
        leader_set.assert_called_with({sentinel.key: 'foo'})
        del leader[sentinel.key]
        leader_set.assert_called_with({sentinel.key: None})

        # Python 2 unicode string values work too
        leader[sentinel.key] = six.u('bar')
        leader_set.assert_called_with({sentinel.key: 'bar'})

        # Byte strings fail under Python 3
        if six.PY3:
            with self.assertRaises(ValueError):
                leader[sentinel.key] = six.b('baz')

        # Non strings fail, as implicit casting causes more trouble
        # than it solves. Simple types like integers would round trip
        # back as strings.
        with self.assertRaises(ValueError):
            leader[sentinel.key] = 42

    @patch.object(hookenv, 'leader_set')
    @patch.object(hookenv, 'leader_get')
    @patch.object(hookenv, 'is_leader')
    def test_set_not_leader(self, is_leader, leader_get, leader_set):
        is_leader.return_value = False
        leader_get.return_value = {'a_key': 'a_value'}
        leader = context.Leader()
        with self.assertRaises(TypeError):
            leader['a_key'] = 'foo'
        with self.assertRaises(TypeError):
            del leader['a_key']
