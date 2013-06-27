import json

import cPickle as pickle
from mock import patch, call, mock_open
from StringIO import StringIO
from mock import MagicMock
from testtools import TestCase
import yaml

from charmhelpers.core import hookenv

CHARM_METADATA = """name: testmock
summary: test mock summary
description: test mock description
requires:
    testreqs:
        interface: mock
provides:
    testprov:
        interface: mock
peers:
    testpeer:
        interface: mock
"""


class SerializableTest(TestCase):
    def test_serializes_object_to_json(self):
        foo = {
            'bar': 'baz',
        }
        wrapped = hookenv.Serializable(foo)
        self.assertEqual(wrapped.json(), json.dumps(foo))

    def test_serializes_object_to_yaml(self):
        foo = {
            'bar': 'baz',
        }
        wrapped = hookenv.Serializable(foo)
        self.assertEqual(wrapped.yaml(), yaml.dump(foo))

    def test_gets_attribute_from_inner_object_as_dict(self):
        foo = {
            'bar': 'baz',
        }
        wrapped = hookenv.Serializable(foo)

        self.assertEqual(wrapped.bar, 'baz')

    def test_raises_error_from_inner_object_as_dict(self):
        foo = {
            'bar': 'baz',
        }
        wrapped = hookenv.Serializable(foo)

        self.assertRaises(AttributeError, getattr, wrapped, 'baz')

    def test_dict_methods_from_inner_object(self):
        foo = {
            'bar': 'baz',
        }
        wrapped = hookenv.Serializable(foo)
        for meth in ('keys', 'values', 'items'):
            self.assertEqual(getattr(wrapped, meth)(), getattr(foo, meth)())

        for meth in ('iterkeys', 'itervalues', 'iteritems'):
            self.assertEqual(list(getattr(wrapped, meth)()),
                             list(getattr(foo, meth)()))
        self.assertEqual(wrapped.get('bar'), foo.get('bar'))
        self.assertEqual(wrapped.get('baz', 42), foo.get('baz', 42))
        self.assertIn('bar', wrapped)

    def test_get_gets_from_inner_object(self):
        foo = {
            'bar': 'baz',
        }
        wrapped = hookenv.Serializable(foo)

        self.assertEqual(wrapped.get('foo'), None)
        self.assertEqual(wrapped.get('bar'), 'baz')
        self.assertEqual(wrapped.get('zoo', 'bla'), 'bla')

    def test_gets_inner_object(self):
        foo = {
            'bar': 'baz',
        }
        wrapped = hookenv.Serializable(foo)

        self.assertIs(wrapped.data, foo)

    def test_pickle(self):
        foo = {'bar': 'baz'}
        wrapped = hookenv.Serializable(foo)
        pickled = pickle.dumps(wrapped)
        unpickled = pickle.loads(pickled)

        self.assert_(isinstance(unpickled, hookenv.Serializable))
        self.assertEqual(unpickled, foo)

    def test_boolean(self):
        true_dict = {'foo': 'bar'}
        false_dict = {}

        self.assertIs(bool(hookenv.Serializable(true_dict)), True)
        self.assertIs(bool(hookenv.Serializable(false_dict)), False)

    def test_equality(self):
        foo = {'bar': 'baz'}
        bar = {'baz': 'bar'}
        wrapped_foo = hookenv.Serializable(foo)

        self.assertEqual(wrapped_foo, foo)
        self.assertEqual(wrapped_foo, wrapped_foo)
        self.assertNotEqual(wrapped_foo, bar)


class HelpersTest(TestCase):
    def setUp(self):
        super(HelpersTest, self).setUp()
        # Reset hookenv cache for each test
        hookenv.cache = {}

    @patch('subprocess.call')
    def test_logs_messages_to_juju_with_default_level(self, mock_call):
        hookenv.log('foo')

        mock_call.assert_called_with(['juju-log', 'foo'])

    @patch('subprocess.call')
    def test_logs_messages_with_alternative_levels(self, mock_call):
        alternative_levels = [
            hookenv.CRITICAL,
            hookenv.ERROR,
            hookenv.WARNING,
            hookenv.INFO,
        ]

        for level in alternative_levels:
            hookenv.log('foo', level)
            mock_call.assert_called_with(['juju-log', '-l', level, 'foo'])

    @patch('subprocess.check_output')
    def test_gets_charm_config_as_serializable(self, check_output):
        config_data = {'foo': 'bar'}
        check_output.return_value = json.dumps(config_data)

        result = hookenv.config()

        self.assert_(isinstance(result, hookenv.Serializable))
        self.assertEqual(result.foo, 'bar')
        check_output.assert_called_with(['config-get', '--format=json'])

    @patch('subprocess.check_output')
    def test_gets_charm_config_with_scope(self, check_output):
        config_data = 'bar'
        check_output.return_value = json.dumps(config_data)

        result = hookenv.config(scope='baz')

        self.assertEqual(result, 'bar')
        check_output.assert_called_with(['config-get', 'baz', '--format=json'])

        # The result can be used like a string
        self.assertEqual(result[1], 'a')

        # ... because the result is actually a string
        self.assert_(isinstance(result, basestring))

    @patch('subprocess.check_output')
    def test_gets_missing_charm_config_with_scope(self, check_output):
        check_output.return_value = ''

        result = hookenv.config(scope='baz')

        self.assertEqual(result, None)
        check_output.assert_called_with(['config-get', 'baz', '--format=json'])

    @patch('charmhelpers.core.hookenv.os')
    def test_gets_the_local_unit(self, os_):
        os_.environ = {
            'JUJU_UNIT_NAME': 'foo',
        }

        self.assertEqual(hookenv.local_unit(), 'foo')

    @patch('charmhelpers.core.hookenv.unit_get')
    def test_gets_unit_private_ip(self, _unitget):
        _unitget.return_value = 'foo'
        self.assertEqual("foo", hookenv.unit_private_ip())
        _unitget.assert_called_with('private-address')

    @patch('charmhelpers.core.hookenv.os')
    def test_checks_that_is_running_in_relation_hook(self, os_):
        os_.environ = {
            'JUJU_RELATION': 'foo',
        }

        self.assertTrue(hookenv.in_relation_hook())

    @patch('charmhelpers.core.hookenv.os')
    def test_checks_that_is_not_running_in_relation_hook(self, os_):
        os_.environ = {
            'bar': 'foo',
        }

        self.assertFalse(hookenv.in_relation_hook())

    @patch('charmhelpers.core.hookenv.os')
    def test_gets_the_relation_type(self, os_):
        os_.environ = {
            'JUJU_RELATION': 'foo',
        }

        self.assertEqual(hookenv.relation_type(), 'foo')

    @patch('charmhelpers.core.hookenv.os')
    def test_relation_type_none_if_not_in_environment(self, os_):
        os_.environ = {}
        self.assertEqual(hookenv.relation_type(), None)

    @patch('subprocess.check_output')
    @patch('charmhelpers.core.hookenv.relation_type')
    def test_gets_relation_ids(self, relation_type, check_output):
        ids = [1, 2, 3]
        check_output.return_value = json.dumps(ids)
        reltype = 'foo'
        relation_type.return_value = reltype

        result = hookenv.relation_ids()

        self.assertEqual(result, ids)
        check_output.assert_called_with(['relation-ids', '--format=json',
                                         reltype])

    @patch('subprocess.check_output')
    @patch('charmhelpers.core.hookenv.relation_type')
    def test_relation_ids_no_relation_type(self, relation_type, check_output):
        ids = [1, 2, 3]
        check_output.return_value = json.dumps(ids)
        relation_type.return_value = None

        result = hookenv.relation_ids()

        self.assertEqual(result, [])

    @patch('subprocess.check_output')
    @patch('charmhelpers.core.hookenv.relation_type')
    def test_gets_relation_ids_for_type(self, relation_type, check_output):
        ids = [1, 2, 3]
        check_output.return_value = json.dumps(ids)
        reltype = 'foo'

        result = hookenv.relation_ids(reltype)

        self.assertEqual(result, ids)
        check_output.assert_called_with(['relation-ids', '--format=json',
                                         reltype])
        self.assertFalse(relation_type.called)

    @patch('subprocess.check_output')
    @patch('charmhelpers.core.hookenv.relation_id')
    def test_gets_related_units(self, relation_id, check_output):
        relid = 123
        units = ['foo', 'bar']
        relation_id.return_value = relid
        check_output.return_value = json.dumps(units)

        result = hookenv.related_units()

        self.assertEqual(result, units)
        check_output.assert_called_with(['relation-list', '--format=json',
                                         '-r', relid])

    @patch('subprocess.check_output')
    @patch('charmhelpers.core.hookenv.relation_id')
    def test_related_units_no_relation(self, relation_id, check_output):
        units = ['foo', 'bar']
        relation_id.return_value = None
        check_output.return_value = json.dumps(units)

        result = hookenv.related_units()

        self.assertEqual(result, units)
        check_output.assert_called_with(['relation-list', '--format=json'])

    @patch('subprocess.check_output')
    @patch('charmhelpers.core.hookenv.relation_id')
    def test_gets_related_units_for_id(self, relation_id, check_output):
        relid = 123
        units = ['foo', 'bar']
        check_output.return_value = json.dumps(units)

        result = hookenv.related_units(relid)

        self.assertEqual(result, units)
        check_output.assert_called_with(['relation-list', '--format=json',
                                         '-r', relid])
        self.assertFalse(relation_id.called)

    @patch('charmhelpers.core.hookenv.os')
    def test_gets_the_remote_unit(self, os_):
        os_.environ = {
            'JUJU_REMOTE_UNIT': 'foo',
        }

        self.assertEqual(hookenv.remote_unit(), 'foo')

    @patch('charmhelpers.core.hookenv.remote_unit')
    @patch('charmhelpers.core.hookenv.relation_get')
    def test_gets_relation_for_unit(self, relation_get, remote_unit):
        unit = 'foo-unit'
        raw_relation = {
            'foo': 'bar',
            'baz-list': '1 2 3',
        }
        remote_unit.return_value = unit
        relation_get.return_value = raw_relation

        result = hookenv.relation_for_unit()

        self.assertEqual(result.__unit__, unit)
        self.assertEqual(getattr(result, 'baz-list'), ['1', '2', '3'])
        relation_get.assert_called_with(unit=unit, rid=None)

    @patch('charmhelpers.core.hookenv.remote_unit')
    @patch('charmhelpers.core.hookenv.relation_get')
    def test_gets_relation_for_specific_unit(self, relation_get, remote_unit):
        unit = 'foo-unit'
        raw_relation = {
            'foo': 'bar',
            'baz-list': '1 2 3',
        }
        relation_get.return_value = raw_relation

        result = hookenv.relation_for_unit(unit)

        self.assertEqual(result.__unit__, unit)
        self.assertEqual(getattr(result, 'baz-list'), ['1', '2', '3'])
        relation_get.assert_called_with(unit=unit, rid=None)
        self.assertFalse(remote_unit.called)

    @patch('charmhelpers.core.hookenv.relation_ids')
    @patch('charmhelpers.core.hookenv.related_units')
    @patch('charmhelpers.core.hookenv.relation_for_unit')
    def test_gets_relations_for_id(self, relation_for_unit, related_units,
                                   relation_ids):
        relid = 123
        units = ['foo', 'bar']
        unit_data = [
            {'foo-item': 'bar-item'},
            {'foo-item2': 'bar-item2'},
        ]
        relation_ids.return_value = relid
        related_units.return_value = units
        relation_for_unit.side_effect = unit_data

        result = hookenv.relations_for_id()

        self.assertEqual(result[0]['__relid__'], relid)
        self.assertEqual(result[0]['foo-item'], 'bar-item')
        self.assertEqual(result[1]['__relid__'], relid)
        self.assertEqual(result[1]['foo-item2'], 'bar-item2')
        related_units.assert_called_with(relid)
        self.assertEqual(relation_for_unit.mock_calls, [
            call('foo', relid),
            call('bar', relid),
        ])

    @patch('charmhelpers.core.hookenv.relation_ids')
    @patch('charmhelpers.core.hookenv.related_units')
    @patch('charmhelpers.core.hookenv.relation_for_unit')
    def test_gets_relations_for_specific_id(self, relation_for_unit,
                                            related_units, relation_ids):
        relid = 123
        units = ['foo', 'bar']
        unit_data = [
            {'foo-item': 'bar-item'},
            {'foo-item2': 'bar-item2'},
        ]
        related_units.return_value = units
        relation_for_unit.side_effect = unit_data

        result = hookenv.relations_for_id(relid)

        self.assertEqual(result[0]['__relid__'], relid)
        self.assertEqual(result[0]['foo-item'], 'bar-item')
        self.assertEqual(result[1]['__relid__'], relid)
        self.assertEqual(result[1]['foo-item2'], 'bar-item2')
        related_units.assert_called_with(relid)
        self.assertEqual(relation_for_unit.mock_calls, [
            call('foo', relid),
            call('bar', relid),
        ])
        self.assertFalse(relation_ids.called)

    @patch('charmhelpers.core.hookenv.in_relation_hook')
    @patch('charmhelpers.core.hookenv.relation_type')
    @patch('charmhelpers.core.hookenv.relation_ids')
    @patch('charmhelpers.core.hookenv.relations_for_id')
    def test_gets_relations_for_type(self, relations_for_id, relation_ids,
                                     relation_type, in_relation_hook):
        reltype = 'foo-type'
        relids = [123, 234]
        relations = [
            [
                {'foo': 'bar'},
                {'foo2': 'bar2'},
            ],
            [
                {'FOO': 'BAR'},
                {'FOO2': 'BAR2'},
            ],
        ]
        is_in_relation = True

        relation_type.return_value = reltype
        relation_ids.return_value = relids
        relations_for_id.side_effect = relations
        in_relation_hook.return_value = is_in_relation

        result = hookenv.relations_of_type()

        self.assertEqual(result[0]['__relid__'], 123)
        self.assertEqual(result[0]['foo'], 'bar')
        self.assertEqual(result[1]['__relid__'], 123)
        self.assertEqual(result[1]['foo2'], 'bar2')
        self.assertEqual(result[2]['__relid__'], 234)
        self.assertEqual(result[2]['FOO'], 'BAR')
        self.assertEqual(result[3]['__relid__'], 234)
        self.assertEqual(result[3]['FOO2'], 'BAR2')
        relation_ids.assert_called_with(reltype)
        self.assertEqual(relations_for_id.mock_calls, [
            call(123),
            call(234),
        ])

    @patch('charmhelpers.core.hookenv.local_unit')
    @patch('charmhelpers.core.hookenv.relation_types')
    @patch('charmhelpers.core.hookenv.relation_ids')
    @patch('charmhelpers.core.hookenv.related_units')
    @patch('charmhelpers.core.hookenv.relation_get')
    def test_gets_relations(self, relation_get, related_units,
                            relation_ids, relation_types, local_unit):
        local_unit.return_value = 'u0'
        relation_types.return_value = ['t1','t2']
        relation_ids.return_value = ['i1']
        related_units.return_value = ['u1', 'u2']
        relation_get.return_value = {'key': 'val'}

        result = hookenv.relations()

        self.assertEqual(result, {
            't1': {
                'i1': {
                    'u0': {'key': 'val'},
                    'u1': {'key': 'val'},
                    'u2': {'key': 'val'},
                 },
            },
            't2': {
                'i1': {
                    'u0': {'key': 'val'},
                    'u1': {'key': 'val'},
                    'u2': {'key': 'val'},
                 },
            },
       })

    @patch('charmhelpers.core.hookenv.config')
    @patch('charmhelpers.core.hookenv.relation_type')
    @patch('charmhelpers.core.hookenv.local_unit')
    @patch('charmhelpers.core.hookenv.relation_id')
    @patch('charmhelpers.core.hookenv.relations')
    @patch('charmhelpers.core.hookenv.relation_get')
    @patch('charmhelpers.core.hookenv.os')
    def test_gets_execution_environment(self, os_, relations_get,
                                        relations, relation_id, local_unit,
                                        relation_type, config):
        config.return_value = 'some-config'
        relation_type.return_value = 'some-type'
        local_unit.return_value = 'some-unit'
        relation_id.return_value = 'some-id'
        relations.return_value = 'all-relations'
        relations_get.return_value = 'some-relations'
        os_.environ = 'some-environment'

        result = hookenv.execution_environment()

        self.assertEqual(result, {
            'conf': 'some-config',
            'reltype': 'some-type',
            'unit': 'some-unit',
            'relid': 'some-id',
            'rel': 'some-relations',
            'rels': 'all-relations',
            'env': 'some-environment',
        })

    @patch('charmhelpers.core.hookenv.os')
    def test_gets_the_relation_id(self, os_):
        os_.environ = {
            'JUJU_RELATION_ID': 'foo',
        }

        self.assertEqual(hookenv.relation_id(), 'foo')

    @patch('charmhelpers.core.hookenv.os')
    def test_relation_id_none_if_no_env(self, os_):
        os_.environ = {}
        self.assertEqual(hookenv.relation_id(), None)

    @patch('subprocess.check_output')
    def test_gets_relation(self, check_output):
        data = {"foo": "BAR"}
        check_output.return_value = json.dumps(data)
        result = hookenv.relation_get()

        self.assertEqual(result.foo, 'BAR')
        check_output.assert_called_with(['relation-get', '--format=json', '-'])

    @patch('subprocess.check_output')
    def test_gets_relation_with_scope(self, check_output):
        check_output.return_value = json.dumps('bar')

        result = hookenv.relation_get(attribute='baz-scope')

        self.assertEqual(result, 'bar')
        check_output.assert_called_with(['relation-get', '--format=json',
                                         'baz-scope'])

    @patch('subprocess.check_output')
    def test_gets_missing_relation_with_scope(self, check_output):
        check_output.return_value = ""

        result = hookenv.relation_get(attribute='baz-scope')

        self.assertEqual(result, None)
        check_output.assert_called_with(['relation-get', '--format=json',
                                         'baz-scope'])

    @patch('subprocess.check_output')
    def test_gets_relation_with_unit_name(self, check_output):
        check_output.return_value = json.dumps('BAR')

        result = hookenv.relation_get(attribute='baz-scope', unit='baz-unit')

        self.assertEqual(result, 'BAR')
        check_output.assert_called_with(['relation-get', '--format=json',
                                         'baz-scope', 'baz-unit'])

    @patch('charmhelpers.core.hookenv.local_unit')
    @patch('subprocess.check_call')
    @patch('subprocess.check_output')
    def test_relation_set_flushes_local_unit_cache(self, check_output,
                                                   check_call, local_unit):
        check_output.return_value = json.dumps('BAR')
        local_unit.return_value = 'baz_unit'
        hookenv.relation_get(attribute='baz_scope', unit='baz_unit')
        hookenv.relation_get(attribute='bar_scope')
        self.assertTrue(len(hookenv.cache) == 2)
        hookenv.relation_set(baz_scope='hello')
        # relation_set should flush any entries for local_unit
        self.assertTrue(len(hookenv.cache) == 1)

    @patch('subprocess.check_output')
    def test_gets_relation_with_relation_id(self, check_output):
        check_output.return_value = json.dumps('BAR')

        result = hookenv.relation_get(attribute='baz-scope', unit='baz-unit',
                                      rid=123)

        self.assertEqual(result, 'BAR')
        check_output.assert_called_with(['relation-get', '--format=json', '-r',
                                         123, 'baz-scope', 'baz-unit'])

    @patch('subprocess.check_call')
    def test_sets_relation_with_kwargs(self, check_call_):
        hookenv.relation_set(foo="bar")
        check_call_.assert_called_with(['relation-set', 'foo=bar'])

    @patch('subprocess.check_call')
    def test_sets_relation_with_dict(self, check_call_):
        hookenv.relation_set(relation_settings={"foo": "bar"})
        check_call_.assert_called_with(['relation-set', 'foo=bar'])

    @patch('subprocess.check_call')
    def test_sets_relation_with_relation_id(self, check_call_):
        hookenv.relation_set(relation_id="foo", bar="baz")
        check_call_.assert_called_with(['relation-set', '-r', 'foo',
                                         'bar=baz'])

    def test_lists_relation_types(self):
        open_ = mock_open()
        open_.return_value = StringIO(CHARM_METADATA)
        with patch('charmhelpers.core.hookenv.open', open_, create=True):
            with patch.dict('os.environ', {'CHARM_DIR': '/var/empty'}):
                reltypes = set(hookenv.relation_types())
        open_.assert_called_once_with('/var/empty/metadata.yaml')
        self.assertEqual(set(('testreqs', 'testprov', 'testpeer')), reltypes)

    @patch('subprocess.check_call')
    def test_opens_port(self, check_call_):
        hookenv.open_port(443, "TCP")
        hookenv.open_port(80)
        hookenv.open_port(100, "UDP")
        calls = [call(['open-port', '443/TCP']),
                 call(['open-port', '80/TCP']),
                 call(['open-port', '100/UDP']),
                ]
        check_call_.assert_has_calls(calls)

    @patch('subprocess.check_call')
    def test_closes_port(self, check_call_):
        hookenv.close_port(443, "TCP")
        hookenv.close_port(80)
        hookenv.close_port(100, "UDP")
        calls = [call(['close-port', '443/TCP']),
                 call(['close-port', '80/TCP']),
                 call(['close-port', '100/UDP']),
                ]
        check_call_.assert_has_calls(calls)

    @patch('subprocess.check_output')
    def test_gets_unit_attribute(self, check_output_):
        check_output_.return_value = json.dumps('bar')
        self.assertEqual(hookenv.unit_get('foo'), 'bar')
        check_output_.assert_called_with(['unit-get', '--format=json', 'foo'])

    @patch('subprocess.check_output')
    def test_gets_missing_unit_attribute(self, check_output_):
        check_output_.return_value = ""
        self.assertEqual(hookenv.unit_get('foo'), None)
        check_output_.assert_called_with(['unit-get', '--format=json', 'foo'])

    def test_cached_decorator(self):
        calls = []
        values = {
            'hello': 'world',
            'foo': 'bar',
            'baz': None
            }

        @hookenv.cached
        def cache_function(attribute):
            calls.append(attribute)
            return values[attribute]

        self.assertEquals(cache_function('hello'), 'world')
        self.assertEquals(cache_function('hello'), 'world')
        self.assertEquals(cache_function('foo'), 'bar')
        self.assertEquals(cache_function('baz'), None)
        self.assertEquals(cache_function('baz'), None)
        self.assertEquals(calls, ['hello', 'foo', 'baz'])

    def test_gets_charm_dir(self):
        with patch.dict('os.environ', {'CHARM_DIR': '/var/empty'}):
            self.assertEqual(hookenv.charm_dir(), '/var/empty')


class HooksTest(TestCase):
    def test_runs_a_registered_function(self):
        foo = MagicMock()
        hooks = hookenv.Hooks()
        hooks.register('foo', foo)

        hooks.execute(['foo', 'some', 'other', 'args'])

        foo.assert_called_with()

    def test_cannot_run_unregistered_function(self):
        foo = MagicMock()
        hooks = hookenv.Hooks()
        hooks.register('foo', foo)

        self.assertRaises(hookenv.UnregisteredHookError, hooks.execute,
                          ['bar'])

    def test_can_run_a_decorated_function_as_one_or_more_hooks(self):
        execs = []
        hooks = hookenv.Hooks()

        @hooks.hook('bar', 'baz')
        def func():
            execs.append(True)

        hooks.execute(['bar'])
        hooks.execute(['baz'])
        self.assertRaises(hookenv.UnregisteredHookError, hooks.execute,
                          ['brew'])
        self.assertEqual(execs, [True, True])

    def test_can_run_a_decorated_function_as_itself(self):
        execs = []
        hooks = hookenv.Hooks()

        @hooks.hook()
        def func():
            execs.append(True)

        hooks.execute(['func'])
        self.assertRaises(hookenv.UnregisteredHookError, hooks.execute,
                          ['brew'])
        self.assertEqual(execs, [True])
