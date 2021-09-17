import os
import json
from subprocess import CalledProcessError
import shutil
import tempfile
import types
from mock import call, MagicMock, mock_open, patch, sentinel
from testtools import TestCase
from enum import Enum
import yaml

import six
import io

from charmhelpers.core import hookenv

if six.PY3:
    import pickle
else:
    import cPickle as pickle


CHARM_METADATA = b"""name: testmock
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


def _clean_globals():
    hookenv.cache.clear()
    del hookenv._atstart[:]
    del hookenv._atexit[:]


class ConfigTest(TestCase):
    def setUp(self):
        super(ConfigTest, self).setUp()

        _clean_globals()
        self.addCleanup(_clean_globals)

        self.charm_dir = tempfile.mkdtemp()
        self.addCleanup(lambda: shutil.rmtree(self.charm_dir))

        patcher = patch.object(hookenv, 'charm_dir', lambda: self.charm_dir)
        self.addCleanup(patcher.stop)
        patcher.start()

    def test_init(self):
        d = dict(foo='bar')
        c = hookenv.Config(d)

        self.assertEqual(c['foo'], 'bar')
        self.assertEqual(c._prev_dict, None)

    def test_init_empty_state_file(self):
        d = dict(foo='bar')
        c = hookenv.Config(d)

        state_path = os.path.join(self.charm_dir, hookenv.Config.CONFIG_FILE_NAME)
        with open(state_path, 'w') as f:
            f.close()

        self.assertEqual(c['foo'], 'bar')
        self.assertEqual(c._prev_dict, None)
        self.assertEqual(c.path, state_path)

    def test_init_invalid_state_file(self):
        d = dict(foo='bar')

        state_path = os.path.join(self.charm_dir, hookenv.Config.CONFIG_FILE_NAME)
        with open(state_path, 'w') as f:
            f.write('blah')

        c = hookenv.Config(d)

        self.assertEqual(c['foo'], 'bar')
        self.assertEqual(c._prev_dict, None)
        self.assertEqual(c.path, state_path)

    def test_load_previous(self):
        d = dict(foo='bar')
        c = hookenv.Config()

        with open(c.path, 'w') as f:
            json.dump(d, f)

        c.load_previous()
        self.assertEqual(c._prev_dict, d)

    def test_load_previous_alternate_path(self):
        d = dict(foo='bar')
        c = hookenv.Config()

        alt_path = os.path.join(self.charm_dir, '.alt-config')
        with open(alt_path, 'w') as f:
            json.dump(d, f)

        c.load_previous(path=alt_path)
        self.assertEqual(c._prev_dict, d)
        self.assertEqual(c.path, alt_path)

    def test_changed_without_prev_dict(self):
        d = dict(foo='bar')
        c = hookenv.Config(d)

        self.assertTrue(c.changed('foo'))

    def test_changed_with_prev_dict(self):
        c = hookenv.Config(dict(foo='bar', a='b'))
        c.save()
        c = hookenv.Config(dict(foo='baz', a='b'))

        self.assertTrue(c.changed('foo'))
        self.assertFalse(c.changed('a'))

    def test_previous_without_prev_dict(self):
        c = hookenv.Config()

        self.assertEqual(c.previous('foo'), None)

    def test_previous_with_prev_dict(self):
        c = hookenv.Config(dict(foo='bar'))
        c.save()
        c = hookenv.Config(dict(foo='baz', a='b'))

        self.assertEqual(c.previous('foo'), 'bar')
        self.assertEqual(c.previous('a'), None)

    def test_save_without_prev_dict(self):
        c = hookenv.Config(dict(foo='bar'))
        c.save()

        with open(c.path, 'r') as f:
            self.assertEqual(c, json.load(f))
            self.assertEqual(c, dict(foo='bar'))
            self.assertEqual(os.stat(c.path).st_mode & 0o777, 0o600)

    def test_save_with_prev_dict(self):
        c = hookenv.Config(dict(foo='bar'))
        c.save()
        c = hookenv.Config(dict(a='b'))
        c.save()

        with open(c.path, 'r') as f:
            self.assertEqual(c, json.load(f))
            self.assertEqual(c, dict(foo='bar', a='b'))
            self.assertEqual(os.stat(c.path).st_mode & 0o777, 0o600)

    def test_deep_change(self):
        # After loading stored data into our previous dictionary,
        # it gets copied into our current dictionary. If this is not
        # a deep copy, then mappings and lists will be shared instances
        # and changes will not be detected.
        c = hookenv.Config(dict(ll=[]))
        c.save()
        c = hookenv.Config()
        c['ll'].append(42)
        self.assertTrue(c.changed('ll'), 'load_previous() did not deepcopy')

    def test_getitem(self):
        c = hookenv.Config(dict(foo='bar'))
        c.save()
        c = hookenv.Config(dict(baz='bam'))

        self.assertRaises(KeyError, lambda: c['missing'])
        self.assertEqual(c['foo'], 'bar')
        self.assertEqual(c['baz'], 'bam')

    def test_get(self):
        c = hookenv.Config(dict(foo='bar'))
        c.save()
        c = hookenv.Config(dict(baz='bam'))

        self.assertIsNone(c.get('missing'))
        self.assertIs(c.get('missing', sentinel.missing), sentinel.missing)
        self.assertEqual(c.get('foo'), 'bar')
        self.assertEqual(c.get('baz'), 'bam')

    def test_keys(self):
        c = hookenv.Config(dict(foo='bar'))
        c["baz"] = "bar"
        self.assertEqual(sorted([six.u("foo"), "baz"]), sorted(c.keys()))

    def test_in(self):
        # Test behavior of the in operator.

        prev_path = os.path.join(hookenv.charm_dir(),
                                 hookenv.Config.CONFIG_FILE_NAME)
        with open(prev_path, 'w') as f:
            json.dump(dict(user='one'), f)
        c = hookenv.Config(dict(charm='one'))

        # Items that exist in the dict exist. Items that don't don't.
        self.assertTrue('user' in c)
        self.assertTrue('charm' in c)
        self.assertFalse('bar' in c)

        # Adding items works as expected.
        c['user'] = 'two'
        c['charm'] = 'two'
        c['bar'] = 'two'
        self.assertTrue('user' in c)
        self.assertTrue('charm' in c)
        self.assertTrue('bar' in c)
        c.save()
        self.assertTrue('user' in c)
        self.assertTrue('charm' in c)
        self.assertTrue('bar' in c)

        # Removing items works as expected.
        del c['user']
        del c['charm']
        self.assertTrue('user' not in c)
        self.assertTrue('charm' not in c)
        c.save()
        self.assertTrue('user' not in c)
        self.assertTrue('charm' not in c)


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
            self.assertEqual(sorted(list(getattr(wrapped, meth)())),
                             sorted(list(getattr(foo, meth)())))

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
        _clean_globals()
        self.addCleanup(_clean_globals)

    @patch('subprocess.call')
    def test_logs_messages_to_juju_with_default_level(self, mock_call):
        hookenv.log('foo')

        mock_call.assert_called_with(['juju-log', 'foo'])

    @patch('subprocess.call')
    def test_logs_messages_object(self, mock_call):
        hookenv.log(object)
        mock_call.assert_called_with(['juju-log', repr(object)])

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

    @patch('subprocess.call')
    def test_function_log_message(self, mock_call):
        hookenv.function_log('foo')
        mock_call.assert_called_with(['function-log', 'foo'])

    @patch('subprocess.call')
    def test_function_log_message_object(self, mock_call):
        hookenv.function_log(object)
        mock_call.assert_called_with(['function-log', repr(object)])

    @patch('charmhelpers.core.hookenv._cache_config', None)
    @patch('charmhelpers.core.hookenv.charm_dir')
    @patch('subprocess.check_output')
    def test_gets_charm_config_with_scope(self, check_output, charm_dir):
        check_output.return_value = json.dumps(dict(baz='bar')).encode('UTF-8')
        charm_dir.return_value = '/nonexistent'

        result = hookenv.config(scope='baz')

        self.assertEqual(result, 'bar')
        check_output.assert_called_with(['config-get', '--all',
                                         '--format=json'])

        # The result can be used like a string
        self.assertEqual(result[1], 'a')

        # ... because the result is actually a string
        self.assert_(isinstance(result, six.string_types))

    @patch('charmhelpers.core.hookenv.log', lambda *args, **kwargs: None)
    @patch('charmhelpers.core.hookenv._cache_config', None)
    @patch('subprocess.check_output')
    def test_gets_missing_charm_config_with_scope(self, check_output):
        check_output.return_value = b''

        result = hookenv.config(scope='baz')

        self.assertEqual(result, None)
        check_output.assert_called_with(['config-get', '--all',
                                         '--format=json'])

    @patch('charmhelpers.core.hookenv._cache_config', None)
    @patch('charmhelpers.core.hookenv.charm_dir')
    @patch('subprocess.check_output')
    def test_gets_config_without_scope(self, check_output, charm_dir):
        check_output.return_value = json.dumps(dict(baz='bar')).encode('UTF-8')
        charm_dir.return_value = '/nonexistent'

        result = hookenv.config()

        self.assertIsInstance(result, hookenv.Config)
        self.assertEqual(result['baz'], 'bar')
        check_output.assert_called_with(['config-get', '--all',
                                         '--format=json'])

    @patch('charmhelpers.core.hookenv.log')
    @patch('charmhelpers.core.hookenv._cache_config', None)
    @patch('charmhelpers.core.hookenv.charm_dir')
    @patch('subprocess.check_output')
    def test_gets_charm_config_invalid_json_with_scope(self,
                                                       check_output,
                                                       charm_dir,
                                                       log):
        check_output.return_value = '{"invalid: "json"}'.encode('UTF-8')
        charm_dir.return_value = '/nonexistent'

        result = hookenv.config(scope='invalid')

        self.assertEqual(result, None)
        cmd_line = ['config-get', '--all', '--format=json']
        check_output.assert_called_with(cmd_line)
        log.assert_called_with(
            'Unable to parse output from config-get: '
            'config_cmd_line="{}" message="{}"'
            .format(str(cmd_line),
                    "Expecting ':' delimiter: line 1 column 13 (char 12)"),
            level=hookenv.ERROR,
        )

    @patch('charmhelpers.core.hookenv.log')
    @patch('charmhelpers.core.hookenv._cache_config', None)
    @patch('charmhelpers.core.hookenv.charm_dir')
    @patch('subprocess.check_output')
    def test_gets_charm_config_invalid_utf8_with_scope(self,
                                                       check_output,
                                                       charm_dir,
                                                       log):
        check_output.return_value = b'{"invalid: "json"}\x9D'
        charm_dir.return_value = '/nonexistent'

        result = hookenv.config(scope='invalid')

        self.assertEqual(result, None)
        cmd_line = ['config-get', '--all', '--format=json']
        check_output.assert_called_with(cmd_line)
        try:
            # Python3
            log.assert_called_with(
                'Unable to parse output from config-get: '
                'config_cmd_line="{}" message="{}"'
                .format(str(cmd_line),
                        "'utf8' codec can't decode byte 0x9d in position "
                        "18: invalid start byte"),
                level=hookenv.ERROR,
            )
        except AssertionError:
            # Python2.7
            log.assert_called_with(
                'Unable to parse output from config-get: '
                'config_cmd_line="{}" message="{}"'
                .format(str(cmd_line),
                        "'utf-8' codec can't decode byte 0x9d in position "
                        "18: invalid start byte"),
                level=hookenv.ERROR,
            )

    @patch('charmhelpers.core.hookenv._cache_config', {'baz': 'bar'})
    @patch('charmhelpers.core.hookenv.charm_dir')
    @patch('subprocess.check_output')
    def test_gets_config_from_cache_without_scope(self,
                                                  check_output,
                                                  charm_dir):
        charm_dir.return_value = '/nonexistent'

        result = hookenv.config()

        self.assertEqual(result['baz'], 'bar')
        self.assertFalse(check_output.called)

    @patch('charmhelpers.core.hookenv._cache_config', {'baz': 'bar'})
    @patch('charmhelpers.core.hookenv.charm_dir')
    @patch('subprocess.check_output')
    def test_gets_config_from_cache_with_scope(self,
                                               check_output,
                                               charm_dir):
        charm_dir.return_value = '/nonexistent'

        result = hookenv.config('baz')

        self.assertEqual(result, 'bar')

        # The result can be used like a string
        self.assertEqual(result[1], 'a')

        # ... because the result is actually a string
        self.assert_(isinstance(result, six.string_types))

        self.assertFalse(check_output.called)

    @patch('charmhelpers.core.hookenv._cache_config', {'foo': 'bar'})
    @patch('subprocess.check_output')
    def test_gets_missing_charm_config_from_cache_with_scope(self,
                                                             check_output):

        result = hookenv.config(scope='baz')

        self.assertEqual(result, None)
        self.assertFalse(check_output.called)

    @patch('charmhelpers.core.hookenv.os')
    def test_gets_the_local_unit(self, os_):
        os_.environ = {
            'JUJU_UNIT_NAME': 'foo',
        }

        self.assertEqual(hookenv.local_unit(), 'foo')

    @patch('charmhelpers.core.hookenv.unit_get')
    def test_gets_unit_public_ip(self, _unitget):
        _unitget.return_value = sentinel.public_ip
        self.assertEqual(sentinel.public_ip, hookenv.unit_public_ip())
        _unitget.assert_called_once_with('public-address')

    @patch('charmhelpers.core.hookenv.unit_get')
    def test_gets_unit_private_ip(self, _unitget):
        _unitget.return_value = sentinel.private_ip
        self.assertEqual(sentinel.private_ip, hookenv.unit_private_ip())
        _unitget.assert_called_once_with('private-address')

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
        check_output.return_value = json.dumps(ids).encode('UTF-8')
        reltype = 'foo'
        relation_type.return_value = reltype

        result = hookenv.relation_ids()

        self.assertEqual(result, ids)
        check_output.assert_called_with(['relation-ids', '--format=json',
                                         reltype])

    @patch('subprocess.check_output')
    @patch('charmhelpers.core.hookenv.relation_type')
    def test_gets_relation_ids_empty_array(self, relation_type, check_output):
        ids = []
        check_output.return_value = json.dumps(None).encode('UTF-8')
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
        check_output.return_value = json.dumps(ids).encode('UTF-8')
        relation_type.return_value = None

        result = hookenv.relation_ids()

        self.assertEqual(result, [])

    @patch('subprocess.check_output')
    @patch('charmhelpers.core.hookenv.relation_type')
    def test_gets_relation_ids_for_type(self, relation_type, check_output):
        ids = [1, 2, 3]
        check_output.return_value = json.dumps(ids).encode('UTF-8')
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
        check_output.return_value = json.dumps(units).encode('UTF-8')

        result = hookenv.related_units()

        self.assertEqual(result, units)
        check_output.assert_called_with(['relation-list', '--format=json',
                                         '-r', relid])

    @patch('subprocess.check_output')
    @patch('charmhelpers.core.hookenv.relation_id')
    def test_gets_related_units_empty_array(self, relation_id, check_output):
        relid = str(123)
        units = []
        relation_id.return_value = relid
        check_output.return_value = json.dumps(None).encode('UTF-8')

        result = hookenv.related_units()

        self.assertEqual(result, units)
        check_output.assert_called_with(['relation-list', '--format=json',
                                         '-r', relid])

    @patch('subprocess.check_output')
    @patch('charmhelpers.core.hookenv.relation_id')
    def test_related_units_no_relation(self, relation_id, check_output):
        units = ['foo', 'bar']
        relation_id.return_value = None
        check_output.return_value = json.dumps(units).encode('UTF-8')

        result = hookenv.related_units()

        self.assertEqual(result, units)
        check_output.assert_called_with(['relation-list', '--format=json'])

    @patch('subprocess.check_output')
    @patch('charmhelpers.core.hookenv.relation_id')
    def test_gets_related_units_for_id(self, relation_id, check_output):
        relid = 123
        units = ['foo', 'bar']
        check_output.return_value = json.dumps(units).encode('UTF-8')

        result = hookenv.related_units(relid)

        self.assertEqual(result, units)
        check_output.assert_called_with(['relation-list', '--format=json',
                                         '-r', relid])
        self.assertFalse(relation_id.called)

    @patch('charmhelpers.core.hookenv.local_unit')
    @patch('charmhelpers.core.hookenv.goal_state')
    @patch('charmhelpers.core.hookenv.has_juju_version')
    def test_gets_expected_peer_units(self, has_juju_version, goal_state,
                                      local_unit):
        has_juju_version.return_value = True
        goal_state.return_value = {
            'units': {
                'keystone/0': {
                    'status': 'active',
                    'since': '2018-09-27 11:38:28Z',
                },
                'keystone/1': {
                    'status': 'active',
                    'since': '2018-09-27 11:39:23Z',
                },
            },
        }
        local_unit.return_value = 'keystone/0'

        result = hookenv.expected_peer_units()

        self.assertIsInstance(result, types.GeneratorType)
        self.assertEqual(sorted(result), ['keystone/1'])
        has_juju_version.assertCalledOnceWith("2.4.0")
        local_unit.assertCalledOnceWith()

    @patch('charmhelpers.core.hookenv.has_juju_version')
    def test_gets_expected_peer_units_wrong_version(self, has_juju_version):
        has_juju_version.return_value = False

        def x():
            # local helper function to make testtools.TestCase.assertRaises
            # work with generator
            list(hookenv.expected_peer_units())

        self.assertRaises(NotImplementedError, x)
        has_juju_version.assertCalledOnceWith("2.4.0")

    @patch('charmhelpers.core.hookenv.goal_state')
    @patch('charmhelpers.core.hookenv.relation_type')
    @patch('charmhelpers.core.hookenv.has_juju_version')
    def test_gets_expected_related_units(self, has_juju_version, relation_type,
                                         goal_state):
        has_juju_version.return_value = True
        relation_type.return_value = 'identity-service'
        goal_state.return_value = {
            'relations': {
                'identity-service': {
                    'glance': {
                        'status': 'joined',
                        'since': '2018-09-27 11:37:16Z'
                    },
                    'glance/0': {
                        'status': 'active',
                        'since': '2018-09-27 11:27:19Z'
                    },
                    'glance/1': {
                        'status': 'active',
                        'since': '2018-09-27 11:27:34Z'
                    },
                },
            },
        }

        result = hookenv.expected_related_units()

        self.assertIsInstance(result, types.GeneratorType)
        self.assertEqual(sorted(result), ['glance/0', 'glance/1'])

    @patch('charmhelpers.core.hookenv.goal_state')
    @patch('charmhelpers.core.hookenv.has_juju_version')
    def test_gets_expected_related_units_for_type(self, has_juju_version,
                                                  goal_state):
        has_juju_version.return_value = True
        goal_state.return_value = {
            'relations': {
                'identity-service': {
                    'glance': {
                        'status': 'joined',
                        'since': '2018-09-27 11:37:16Z'
                    },
                    'glance/0': {
                        'status': 'active',
                        'since': '2018-09-27 11:27:19Z'
                    },
                    'glance/1': {
                        'status': 'active',
                        'since': '2018-09-27 11:27:34Z'
                    },
                },
            },
        }

        result = hookenv.expected_related_units('identity-service')

        self.assertIsInstance(result, types.GeneratorType)
        self.assertEqual(sorted(result), ['glance/0', 'glance/1'])

    @patch('charmhelpers.core.hookenv.has_juju_version')
    def test_gets_expected_related_units_wrong_version(self, has_juju_version):
        has_juju_version.return_value = False

        def x():
            # local helper function to make testtools.TestCase.assertRaises
            # work with generator
            list(hookenv.expected_related_units())

        self.assertRaises(NotImplementedError, x)
        has_juju_version.assertCalledOnceWith("2.4.4")

    @patch('charmhelpers.core.hookenv.os')
    def test_gets_the_departing_unit(self, os_):
        os_.environ = {
            'JUJU_DEPARTING_UNIT': 'foo/0',
        }

        self.assertEqual(hookenv.departing_unit(), 'foo/0')

    @patch('charmhelpers.core.hookenv.os')
    def test_no_departing_unit(self, os_):
        os_.environ = {}
        self.assertEqual(hookenv.departing_unit(), None)

    @patch('charmhelpers.core.hookenv.os')
    def test_gets_the_remote_unit(self, os_):
        os_.environ = {
            'JUJU_REMOTE_UNIT': 'foo',
        }

        self.assertEqual(hookenv.remote_unit(), 'foo')

    @patch('charmhelpers.core.hookenv.os')
    def test_no_remote_unit(self, os_):
        os_.environ = {}
        self.assertEqual(hookenv.remote_unit(), None)

    @patch('charmhelpers.core.hookenv.remote_unit')
    @patch('charmhelpers.core.hookenv.relation_get')
    def test_gets_relation_for_unit(self, relation_get, remote_unit):
        unit = 'foo-unit'
        raw_relation = {
            'foo': 'bar',
        }
        remote_unit.return_value = unit
        relation_get.return_value = raw_relation

        result = hookenv.relation_for_unit()

        self.assertEqual(result['__unit__'], unit)
        self.assertEqual(result['foo'], 'bar')
        relation_get.assert_called_with(unit=unit, rid=None)

    @patch('charmhelpers.core.hookenv.remote_unit')
    @patch('charmhelpers.core.hookenv.relation_get')
    def test_gets_relation_for_unit_with_list(self, relation_get, remote_unit):
        unit = 'foo-unit'
        raw_relation = {
            'foo-list': 'one two three',
        }
        remote_unit.return_value = unit
        relation_get.return_value = raw_relation

        result = hookenv.relation_for_unit()

        self.assertEqual(result['__unit__'], unit)
        self.assertEqual(result['foo-list'], ['one', 'two', 'three'])
        relation_get.assert_called_with(unit=unit, rid=None)

    @patch('charmhelpers.core.hookenv.remote_unit')
    @patch('charmhelpers.core.hookenv.relation_get')
    def test_gets_relation_for_specific_unit(self, relation_get, remote_unit):
        unit = 'foo-unit'
        raw_relation = {
            'foo': 'bar',
        }
        relation_get.return_value = raw_relation

        result = hookenv.relation_for_unit(unit)

        self.assertEqual(result['__unit__'], unit)
        self.assertEqual(result['foo'], 'bar')
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
        relation_types.return_value = ['t1', 't2']
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

    @patch('charmhelpers.core.hookenv.relation_set')
    @patch('charmhelpers.core.hookenv.relation_get')
    @patch('charmhelpers.core.hookenv.local_unit')
    def test_relation_clear(self, local_unit,
                            relation_get,
                            relation_set):
        local_unit.return_value = 'local-unit'
        relation_get.return_value = {
            'private-address': '10.5.0.1',
            'foo': 'bar',
            'public-address': '146.192.45.6'
        }
        hookenv.relation_clear('relation:1')
        relation_get.assert_called_with(rid='relation:1',
                                        unit='local-unit')
        relation_set.assert_called_with(
            relation_id='relation:1',
            **{'private-address': '10.5.0.1',
               'foo': None,
               'public-address': '146.192.45.6'})

    @patch('charmhelpers.core.hookenv.relation_ids')
    @patch('charmhelpers.core.hookenv.related_units')
    @patch('charmhelpers.core.hookenv.relation_get')
    def test_is_relation_made(self, relation_get, related_units,
                              relation_ids):
        relation_get.return_value = 'hostname'
        related_units.return_value = ['test/1']
        relation_ids.return_value = ['test:0']
        self.assertTrue(hookenv.is_relation_made('test'))
        relation_get.assert_called_with('private-address',
                                        rid='test:0', unit='test/1')

    @patch('charmhelpers.core.hookenv.relation_ids')
    @patch('charmhelpers.core.hookenv.related_units')
    @patch('charmhelpers.core.hookenv.relation_get')
    def test_is_relation_made_multi_unit(self, relation_get, related_units,
                                         relation_ids):
        relation_get.side_effect = [None, 'hostname']
        related_units.return_value = ['test/1', 'test/2']
        relation_ids.return_value = ['test:0']
        self.assertTrue(hookenv.is_relation_made('test'))

    @patch('charmhelpers.core.hookenv.relation_ids')
    @patch('charmhelpers.core.hookenv.related_units')
    @patch('charmhelpers.core.hookenv.relation_get')
    def test_is_relation_made_different_key(self,
                                            relation_get, related_units,
                                            relation_ids):
        relation_get.return_value = 'hostname'
        related_units.return_value = ['test/1']
        relation_ids.return_value = ['test:0']
        self.assertTrue(hookenv.is_relation_made('test', keys='auth'))
        relation_get.assert_called_with('auth',
                                        rid='test:0', unit='test/1')

    @patch('charmhelpers.core.hookenv.relation_ids')
    @patch('charmhelpers.core.hookenv.related_units')
    @patch('charmhelpers.core.hookenv.relation_get')
    def test_is_relation_made_multiple_keys(self,
                                            relation_get, related_units,
                                            relation_ids):
        relation_get.side_effect = ['password', 'hostname']
        related_units.return_value = ['test/1']
        relation_ids.return_value = ['test:0']
        self.assertTrue(hookenv.is_relation_made('test',
                                                 keys=['auth', 'host']))
        relation_get.assert_has_calls(
            [call('auth', rid='test:0', unit='test/1'),
             call('host', rid='test:0', unit='test/1')]
        )

    @patch('charmhelpers.core.hookenv.relation_ids')
    @patch('charmhelpers.core.hookenv.related_units')
    @patch('charmhelpers.core.hookenv.relation_get')
    def test_is_relation_made_not_made(self,
                                       relation_get, related_units,
                                       relation_ids):
        relation_get.return_value = None
        related_units.return_value = ['test/1']
        relation_ids.return_value = ['test:0']
        self.assertFalse(hookenv.is_relation_made('test'))

    @patch('charmhelpers.core.hookenv.relation_ids')
    @patch('charmhelpers.core.hookenv.related_units')
    @patch('charmhelpers.core.hookenv.relation_get')
    def test_is_relation_made_not_made_multiple_keys(self,
                                                     relation_get,
                                                     related_units,
                                                     relation_ids):
        relation_get.side_effect = ['password', None]
        related_units.return_value = ['test/1']
        relation_ids.return_value = ['test:0']
        self.assertFalse(hookenv.is_relation_made('test',
                                                  keys=['auth', 'host']))
        relation_get.assert_has_calls(
            [call('auth', rid='test:0', unit='test/1'),
             call('host', rid='test:0', unit='test/1')]
        )

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

    @patch('charmhelpers.core.hookenv.config')
    @patch('charmhelpers.core.hookenv.relation_type')
    @patch('charmhelpers.core.hookenv.local_unit')
    @patch('charmhelpers.core.hookenv.relation_id')
    @patch('charmhelpers.core.hookenv.relations')
    @patch('charmhelpers.core.hookenv.relation_get')
    @patch('charmhelpers.core.hookenv.os')
    def test_gets_execution_environment_no_relation(
            self, os_, relations_get, relations, relation_id,
            local_unit, relation_type, config):
        config.return_value = 'some-config'
        relation_type.return_value = 'some-type'
        local_unit.return_value = 'some-unit'
        relation_id.return_value = None
        relations.return_value = 'all-relations'
        relations_get.return_value = 'some-relations'
        os_.environ = 'some-environment'

        result = hookenv.execution_environment()

        self.assertEqual(result, {
            'conf': 'some-config',
            'unit': 'some-unit',
            'rels': 'all-relations',
            'env': 'some-environment',
        })

    @patch('charmhelpers.core.hookenv.remote_service_name')
    @patch('charmhelpers.core.hookenv.relation_ids')
    @patch('charmhelpers.core.hookenv.os')
    def test_gets_the_relation_id(self, os_, relation_ids, remote_service_name):
        os_.environ = {
            'JUJU_RELATION_ID': 'foo',
        }

        self.assertEqual(hookenv.relation_id(), 'foo')

        relation_ids.return_value = ['r:1', 'r:2']
        remote_service_name.side_effect = ['other', 'service']
        self.assertEqual(hookenv.relation_id('rel', 'service/0'), 'r:2')
        relation_ids.assert_called_once_with('rel')
        self.assertEqual(remote_service_name.call_args_list, [
            call('r:1'),
            call('r:2'),
        ])
        remote_service_name.side_effect = ['other', 'service']
        self.assertEqual(hookenv.relation_id('rel', 'service'), 'r:2')

    @patch('charmhelpers.core.hookenv.os')
    def test_relation_id_none_if_no_env(self, os_):
        os_.environ = {}
        self.assertEqual(hookenv.relation_id(), None)

    @patch('subprocess.check_output')
    def test_gets_relation(self, check_output):
        data = {"foo": "BAR"}
        check_output.return_value = json.dumps(data).encode('UTF-8')
        result = hookenv.relation_get()

        self.assertEqual(result['foo'], 'BAR')
        check_output.assert_called_with(['relation-get', '--format=json', '-'])

        hookenv.relation_get(unit='foo/0')
        check_output.assert_called_with(['relation-get', '--format=json', '-', 'foo/0'])

        hookenv.relation_get(app='foo')
        check_output.assert_called_with(['relation-get', '--format=json', '--app', '-', 'foo'])

        self.assertRaises(ValueError, hookenv.relation_get, app='foo', unit='foo/0')

    @patch('charmhelpers.core.hookenv.subprocess')
    def test_relation_get_none(self, mock_subprocess):
        mock_subprocess.check_output.return_value = b'null'

        result = hookenv.relation_get()

        self.assertIsNone(result)

    @patch('charmhelpers.core.hookenv.subprocess')
    def test_relation_get_calledprocesserror(self, mock_subprocess):
        """relation-get called outside a relation will errors without id."""
        mock_subprocess.check_output.side_effect = CalledProcessError(
            2, '/foo/bin/relation-get'
            'no relation id specified')

        result = hookenv.relation_get()

        self.assertIsNone(result)

    @patch('charmhelpers.core.hookenv.subprocess')
    def test_relation_get_calledprocesserror_other(self, mock_subprocess):
        """relation-get can fail for other more serious errors."""
        mock_subprocess.check_output.side_effect = CalledProcessError(
            1, '/foo/bin/relation-get'
            'connection refused')

        self.assertRaises(CalledProcessError, hookenv.relation_get)

    @patch('subprocess.check_output')
    def test_gets_relation_with_scope(self, check_output):
        check_output.return_value = json.dumps('bar').encode('UTF-8')

        result = hookenv.relation_get(attribute='baz-scope')

        self.assertEqual(result, 'bar')
        check_output.assert_called_with(['relation-get', '--format=json',
                                         'baz-scope'])

    @patch('subprocess.check_output')
    def test_gets_missing_relation_with_scope(self, check_output):
        check_output.return_value = b""

        result = hookenv.relation_get(attribute='baz-scope')

        self.assertEqual(result, None)
        check_output.assert_called_with(['relation-get', '--format=json',
                                         'baz-scope'])

    @patch('subprocess.check_output')
    def test_gets_relation_with_unit_name(self, check_output):
        check_output.return_value = json.dumps('BAR').encode('UTF-8')

        result = hookenv.relation_get(attribute='baz-scope', unit='baz-unit')

        self.assertEqual(result, 'BAR')
        check_output.assert_called_with(['relation-get', '--format=json',
                                         'baz-scope', 'baz-unit'])

    @patch('charmhelpers.core.hookenv.local_unit')
    @patch('subprocess.check_call')
    @patch('subprocess.check_output')
    def test_relation_set_flushes_local_unit_cache(self, check_output,
                                                   check_call, local_unit):
        check_output.return_value = json.dumps('BAR').encode('UTF-8')
        local_unit.return_value = 'baz_unit'
        hookenv.relation_get(attribute='baz_scope', unit='baz_unit')
        hookenv.relation_get(attribute='bar_scope')
        self.assertTrue(len(hookenv.cache) == 2)
        check_output.return_value = ""
        hookenv.relation_set(baz_scope='hello')
        # relation_set should flush any entries for local_unit
        self.assertTrue(len(hookenv.cache) == 1)

    @patch('subprocess.check_output')
    def test_gets_relation_with_relation_id(self, check_output):
        check_output.return_value = json.dumps('BAR').encode('UTF-8')

        result = hookenv.relation_get(attribute='baz-scope', unit='baz-unit',
                                      rid=123)

        self.assertEqual(result, 'BAR')
        check_output.assert_called_with(['relation-get', '--format=json', '-r',
                                         123, 'baz-scope', 'baz-unit'])

    @patch('charmhelpers.core.hookenv.local_unit')
    @patch('subprocess.check_output')
    @patch('subprocess.check_call')
    def test_sets_relation_with_kwargs(self, check_call_, check_output,
                                       local_unit):
        hookenv.relation_set(foo="bar")
        check_call_.assert_called_with(['relation-set', 'foo=bar'])

        hookenv.relation_set(foo="bar", app=True)
        check_call_.assert_called_with(['relation-set', '--app', 'foo=bar'])

    @patch('charmhelpers.core.hookenv.local_unit')
    @patch('subprocess.check_output')
    @patch('subprocess.check_call')
    def test_sets_relation_with_dict(self, check_call_, check_output,
                                     local_unit):
        hookenv.relation_set(relation_settings={"foo": "bar"})
        check_call_.assert_called_with(['relation-set', 'foo=bar'])

    @patch('charmhelpers.core.hookenv.local_unit')
    @patch('subprocess.check_output')
    @patch('subprocess.check_call')
    def test_sets_relation_with_relation_id(self, check_call_, check_output,
                                            local_unit):
        hookenv.relation_set(relation_id="foo", bar="baz")
        check_call_.assert_called_with(['relation-set', '-r', 'foo',
                                        'bar=baz'])

    @patch('charmhelpers.core.hookenv.local_unit')
    @patch('subprocess.check_output')
    @patch('subprocess.check_call')
    def test_sets_relation_with_missing_value(self, check_call_, check_output,
                                              local_unit):
        hookenv.relation_set(foo=None)
        check_call_.assert_called_with(['relation-set', 'foo='])

    @patch('charmhelpers.core.hookenv.local_unit', MagicMock())
    @patch('os.remove')
    @patch('subprocess.check_output')
    @patch('subprocess.check_call')
    def test_relation_set_file(self, check_call, check_output, remove):
        """If relation-set accepts a --file parameter, it's used.

        Juju 1.23.2 introduced a --file parameter, which means you can
        pass the data through a file. Not using --file would make
        relation_set break if the relation data is too big.
        """
        # check_output(["relation-set", "--help"]) is used to determine
        # whether we can pass --file to it.
        check_output.return_value = "--file"
        hookenv.relation_set(foo="bar")
        check_output.assert_called_with(
            ["relation-set", "--help"], universal_newlines=True)
        # relation-set is called with relation-set --file <temp_file>
        # with data as YAML and the temp_file is then removed.
        self.assertEqual(1, len(check_call.call_args[0]))
        command = check_call.call_args[0][0]
        self.assertEqual(3, len(command))
        self.assertEqual("relation-set", command[0])
        self.assertEqual("--file", command[1])
        temp_file = command[2]
        with open(temp_file, "r") as f:
            self.assertEqual("foo: bar", f.read().strip())
        remove.assert_called_with(temp_file)

    @patch('charmhelpers.core.hookenv.local_unit', MagicMock())
    @patch('os.remove')
    @patch('subprocess.check_output')
    @patch('subprocess.check_call')
    def test_relation_set_file_non_str(self, check_call, check_output, remove):
        """If relation-set accepts a --file parameter, it's used.

        Any value that is not a string is converted to a string before encoding
        the settings to YAML.
        """
        # check_output(["relation-set", "--help"]) is used to determine
        # whether we can pass --file to it.
        check_output.return_value = "--file"
        hookenv.relation_set(foo={"bar": 1})
        check_output.assert_called_with(
            ["relation-set", "--help"], universal_newlines=True)
        # relation-set is called with relation-set --file <temp_file>
        # with data as YAML and the temp_file is then removed.
        self.assertEqual(1, len(check_call.call_args[0]))
        command = check_call.call_args[0][0]
        self.assertEqual(3, len(command))
        self.assertEqual("relation-set", command[0])
        self.assertEqual("--file", command[1])
        temp_file = command[2]
        with open(temp_file, "r") as f:
            self.assertEqual("foo: '{''bar'': 1}'", f.read().strip())
        remove.assert_called_with(temp_file)

    def test_lists_relation_types(self):
        open_ = mock_open()
        open_.return_value = io.BytesIO(CHARM_METADATA)

        with patch('charmhelpers.core.hookenv.open', open_, create=True):
            with patch.dict('os.environ', {'CHARM_DIR': '/var/empty'}):
                reltypes = set(hookenv.relation_types())
        open_.assert_called_once_with('/var/empty/metadata.yaml')
        self.assertEqual(set(('testreqs', 'testprov', 'testpeer')), reltypes)

    def test_metadata(self):
        open_ = mock_open()
        open_.return_value = io.BytesIO(CHARM_METADATA)

        with patch('charmhelpers.core.hookenv.open', open_, create=True):
            with patch.dict('os.environ', {'CHARM_DIR': '/var/empty'}):
                metadata = hookenv.metadata()
        self.assertEqual(metadata, yaml.safe_load(CHARM_METADATA))

    @patch('charmhelpers.core.hookenv.relation_ids')
    @patch('charmhelpers.core.hookenv.metadata')
    def test_peer_relation_id(self, metadata, relation_ids):
        metadata.return_value = {'peers': {sentinel.peer_relname: {}}}
        relation_ids.return_value = [sentinel.pid1, sentinel.pid2]
        self.assertEqual(hookenv.peer_relation_id(), sentinel.pid1)
        relation_ids.assert_called_once_with(sentinel.peer_relname)

    def test_charm_name(self):
        open_ = mock_open()
        open_.return_value = io.BytesIO(CHARM_METADATA)

        with patch('charmhelpers.core.hookenv.open', open_, create=True):
            with patch.dict('os.environ', {'CHARM_DIR': '/var/empty'}):
                charm_name = hookenv.charm_name()
        self.assertEqual("testmock", charm_name)

    @patch('subprocess.check_call')
    def test_opens_port(self, check_call_):
        hookenv.open_port(443, "TCP")
        hookenv.open_port(80)
        hookenv.open_port(100, "UDP")
        hookenv.open_port(0, "ICMP")
        calls = [
            call(['open-port', '443/TCP']),
            call(['open-port', '80/TCP']),
            call(['open-port', '100/UDP']),
            call(['open-port', 'ICMP']),
        ]
        check_call_.assert_has_calls(calls)

    @patch('subprocess.check_call')
    def test_closes_port(self, check_call_):
        hookenv.close_port(443, "TCP")
        hookenv.close_port(80)
        hookenv.close_port(100, "UDP")
        hookenv.close_port(0, "ICMP")
        calls = [
            call(['close-port', '443/TCP']),
            call(['close-port', '80/TCP']),
            call(['close-port', '100/UDP']),
            call(['close-port', 'ICMP']),
        ]
        check_call_.assert_has_calls(calls)

    @patch('subprocess.check_call')
    def test_opens_ports(self, check_call_):
        hookenv.open_ports(443, 447, "TCP")
        hookenv.open_ports(80, 91)
        hookenv.open_ports(100, 200, "UDP")
        calls = [
            call(['open-port', '443-447/TCP']),
            call(['open-port', '80-91/TCP']),
            call(['open-port', '100-200/UDP']),
        ]
        check_call_.assert_has_calls(calls)

    @patch('subprocess.check_call')
    def test_closes_ports(self, check_call_):
        hookenv.close_ports(443, 447, "TCP")
        hookenv.close_ports(80, 91)
        hookenv.close_ports(100, 200, "UDP")
        calls = [
            call(['close-port', '443-447/TCP']),
            call(['close-port', '80-91/TCP']),
            call(['close-port', '100-200/UDP']),
        ]
        check_call_.assert_has_calls(calls)

    @patch('subprocess.check_output')
    def test_gets_opened_ports(self, check_output_):
        prts = ['8080/tcp', '8081-8083/tcp']
        check_output_.return_value = json.dumps(prts).encode('UTF-8')
        self.assertEqual(hookenv.opened_ports(), prts)
        check_output_.assert_called_with(['opened-ports', '--format=json'])

    @patch('subprocess.check_output')
    def test_gets_unit_attribute(self, check_output_):
        check_output_.return_value = json.dumps('bar').encode('UTF-8')
        self.assertEqual(hookenv.unit_get('foo'), 'bar')
        check_output_.assert_called_with(['unit-get', '--format=json', 'foo'])

    @patch('subprocess.check_output')
    def test_gets_missing_unit_attribute(self, check_output_):
        check_output_.return_value = b""
        self.assertEqual(hookenv.unit_get('foo'), None)
        check_output_.assert_called_with(['unit-get', '--format=json', 'foo'])

    def test_cached_decorator(self):
        class Unserializable(object):
            def __str__(self):
                return 'unserializable'

        unserializable = Unserializable()
        calls = []
        values = {
            'hello': 'world',
            'foo': 'bar',
            'baz': None,
            unserializable: 'qux',
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
        self.assertEquals(cache_function(unserializable), 'qux')
        self.assertEquals(calls, ['hello', 'foo', 'baz', unserializable])

    def test_gets_charm_dir(self):
        with patch.dict('os.environ', {}):
            self.assertEqual(hookenv.charm_dir(), None)
        with patch.dict('os.environ', {'CHARM_DIR': '/var/empty'}):
            self.assertEqual(hookenv.charm_dir(), '/var/empty')
        with patch.dict('os.environ', {'JUJU_CHARM_DIR': '/var/another'}):
            self.assertEqual(hookenv.charm_dir(), '/var/another')

    @patch('subprocess.check_output')
    def test_resource_get_unsupported(self, check_output_):
        check_output_.side_effect = OSError(2, 'resource-get')
        self.assertRaises(NotImplementedError, hookenv.resource_get, 'foo')

    @patch('subprocess.check_output')
    def test_resource_get(self, check_output_):
        check_output_.return_value = b'/tmp/file'
        self.assertEqual(hookenv.resource_get('file'), '/tmp/file')
        check_output_.side_effect = CalledProcessError(
            1, '/foo/bin/resource-get',
            'error: could not download resource: resource#foo/file not found')
        self.assertFalse(hookenv.resource_get('no-file'))
        self.assertFalse(hookenv.resource_get(None))

    @patch('subprocess.check_output')
    def test_goal_state_unsupported(self, check_output_):
        check_output_.side_effect = OSError(2, 'goal-state')
        self.assertRaises(NotImplementedError, hookenv.goal_state)

    @patch('subprocess.check_output')
    def test_goal_state(self, check_output_):
        expect = {
            'units': {},
            'relations': {},
        }
        check_output_.return_value = json.dumps(expect).encode('UTF-8')
        result = hookenv.goal_state()

        self.assertEqual(result, expect)
        check_output_.assert_called_with(['goal-state', '--format=json'])

    @patch('subprocess.check_output')
    def test_is_leader_unsupported(self, check_output_):
        check_output_.side_effect = OSError(2, 'is-leader')
        self.assertRaises(NotImplementedError, hookenv.is_leader)

    @patch('subprocess.check_output')
    def test_is_leader(self, check_output_):
        check_output_.return_value = b'false'
        self.assertFalse(hookenv.is_leader())
        check_output_.return_value = b'true'
        self.assertTrue(hookenv.is_leader())

    @patch('subprocess.check_call')
    def test_payload_register(self, check_call_):
        hookenv.payload_register('monitoring', 'docker', 'abc123')
        check_call_.assert_called_with(['payload-register', 'monitoring',
                                        'docker', 'abc123'])

    @patch('subprocess.check_call')
    def test_payload_unregister(self, check_call_):
        hookenv.payload_unregister('monitoring', 'abc123')
        check_call_.assert_called_with(['payload-unregister', 'monitoring',
                                        'abc123'])

    @patch('subprocess.check_call')
    def test_payload_status_set(self, check_call_):
        hookenv.payload_status_set('monitoring', 'abc123', 'Running')
        check_call_.assert_called_with(['payload-status-set', 'monitoring',
                                        'abc123', 'Running'])

    @patch('subprocess.check_call')
    def test_application_version_set(self, check_call_):
        hookenv.application_version_set('v1.2.3')
        check_call_.assert_called_with(['application-version-set', 'v1.2.3'])

    @patch.object(os, 'getenv')
    @patch.object(hookenv, 'log')
    def test_env_proxy_settings_juju_charm_all_selected(self, faux_log,
                                                        get_env):
        expected_settings = {
            'HTTP_PROXY': 'http://squid.internal:3128',
            'http_proxy': 'http://squid.internal:3128',
            'HTTPS_PROXY': 'https://squid.internals:3128',
            'https_proxy': 'https://squid.internals:3128',
            'NO_PROXY': '192.0.2.0/24,198.51.100.0/24,.bar.com',
            'no_proxy': '192.0.2.0/24,198.51.100.0/24,.bar.com',
            'FTP_PROXY': 'ftp://ftp.internal:21',
            'ftp_proxy': 'ftp://ftp.internal:21',
        }

        def get_env_side_effect(var):
            return {
                'HTTP_PROXY': None,
                'HTTPS_PROXY': None,
                'NO_PROXY': None,
                'FTP_PROXY': None,
                'JUJU_CHARM_HTTP_PROXY': 'http://squid.internal:3128',
                'JUJU_CHARM_HTTPS_PROXY': 'https://squid.internals:3128',
                'JUJU_CHARM_FTP_PROXY': 'ftp://ftp.internal:21',
                'JUJU_CHARM_NO_PROXY': '192.0.2.0/24,198.51.100.0/24,.bar.com'
            }[var]
        get_env.side_effect = get_env_side_effect

        proxy_settings = hookenv.env_proxy_settings()
        get_env.assert_has_calls([call("HTTP_PROXY"),
                                 call("HTTPS_PROXY"),
                                 call("NO_PROXY"),
                                 call("FTP_PROXY"),
                                 call("JUJU_CHARM_HTTP_PROXY"),
                                 call("JUJU_CHARM_HTTPS_PROXY"),
                                 call("JUJU_CHARM_FTP_PROXY"),
                                 call("JUJU_CHARM_NO_PROXY")],
                                 any_order=True)
        self.assertEqual(expected_settings, proxy_settings)
        # Verify that we logged a warning about the cidr in NO_PROXY.
        faux_log.assert_called_with(hookenv.RANGE_WARNING,
                                    level=hookenv.WARNING)

    @patch.object(os, 'getenv')
    def test_env_proxy_settings_legacy_https(self, get_env):
        expected_settings = {
            'HTTPS_PROXY': 'http://squid.internal:3128',
            'https_proxy': 'http://squid.internal:3128',
        }

        def get_env_side_effect(var):
            return {
                'HTTPS_PROXY': 'http://squid.internal:3128',
                'JUJU_CHARM_HTTPS_PROXY': None,
            }[var]
        get_env.side_effect = get_env_side_effect

        proxy_settings = hookenv.env_proxy_settings(['https'])
        get_env.assert_has_calls([call("HTTPS_PROXY"),
                                 call("JUJU_CHARM_HTTPS_PROXY")],
                                 any_order=True)
        self.assertEqual(expected_settings, proxy_settings)

    @patch.object(os, 'getenv')
    def test_env_proxy_settings_juju_charm_https(self, get_env):
        expected_settings = {
            'HTTPS_PROXY': 'http://squid.internal:3128',
            'https_proxy': 'http://squid.internal:3128',
        }

        def get_env_side_effect(var):
            return {
                'HTTPS_PROXY': None,
                'JUJU_CHARM_HTTPS_PROXY': 'http://squid.internal:3128',
            }[var]
        get_env.side_effect = get_env_side_effect

        proxy_settings = hookenv.env_proxy_settings(['https'])
        get_env.assert_has_calls([call("HTTPS_PROXY"),
                                 call("JUJU_CHARM_HTTPS_PROXY")],
                                 any_order=True)
        self.assertEqual(expected_settings, proxy_settings)

    @patch.object(os, 'getenv')
    def test_env_proxy_settings_legacy_http(self, get_env):
        expected_settings = {
            'HTTP_PROXY': 'http://squid.internal:3128',
            'http_proxy': 'http://squid.internal:3128',
        }

        def get_env_side_effect(var):
            return {
                'HTTP_PROXY': 'http://squid.internal:3128',
                'JUJU_CHARM_HTTP_PROXY': None,
            }[var]
        get_env.side_effect = get_env_side_effect

        proxy_settings = hookenv.env_proxy_settings(['http'])
        get_env.assert_has_calls([call("HTTP_PROXY"),
                                 call("JUJU_CHARM_HTTP_PROXY")],
                                 any_order=True)
        self.assertEqual(expected_settings, proxy_settings)

    @patch.object(os, 'getenv')
    def test_env_proxy_settings_juju_charm_http(self, get_env):
        expected_settings = {
            'HTTP_PROXY': 'http://squid.internal:3128',
            'http_proxy': 'http://squid.internal:3128',
        }

        def get_env_side_effect(var):
            return {
                'HTTP_PROXY': None,
                'JUJU_CHARM_HTTP_PROXY': 'http://squid.internal:3128',
            }[var]
        get_env.side_effect = get_env_side_effect

        proxy_settings = hookenv.env_proxy_settings(['http'])
        get_env.assert_has_calls([call("HTTP_PROXY"),
                                 call("JUJU_CHARM_HTTP_PROXY")],
                                 any_order=True)
        self.assertEqual(expected_settings, proxy_settings)

    @patch.object(hookenv, 'metadata')
    def test_is_subordinate(self, mock_metadata):
        mock_metadata.return_value = {}
        self.assertFalse(hookenv.is_subordinate())
        mock_metadata.return_value = {'subordinate': False}
        self.assertFalse(hookenv.is_subordinate())
        mock_metadata.return_value = {'subordinate': True}
        self.assertTrue(hookenv.is_subordinate())


class HooksTest(TestCase):
    def setUp(self):
        super(HooksTest, self).setUp()

        _clean_globals()
        self.addCleanup(_clean_globals)

        charm_dir = tempfile.mkdtemp()
        self.addCleanup(lambda: shutil.rmtree(charm_dir))
        patcher = patch.object(hookenv, 'charm_dir', lambda: charm_dir)
        self.addCleanup(patcher.stop)
        patcher.start()

        config = hookenv.Config({})

        def _mock_config(scope=None):
            return config if scope is None else config[scope]
        patcher = patch.object(hookenv, 'config', _mock_config)
        self.addCleanup(patcher.stop)
        patcher.start()

    def test_config_saved_after_execute(self):
        config = hookenv.config()
        config.implicit_save = True

        foo = MagicMock()
        hooks = hookenv.Hooks()
        hooks.register('foo', foo)
        hooks.execute(['foo', 'some', 'other', 'args'])
        self.assertTrue(os.path.exists(config.path))

    def test_config_not_saved_after_execute(self):
        config = hookenv.config()
        config.implicit_save = False

        foo = MagicMock()
        hooks = hookenv.Hooks()
        hooks.register('foo', foo)
        hooks.execute(['foo', 'some', 'other', 'args'])
        self.assertFalse(os.path.exists(config.path))

    def test_config_save_disabled(self):
        config = hookenv.config()
        config.implicit_save = True

        foo = MagicMock()
        hooks = hookenv.Hooks(config_save=False)
        hooks.register('foo', foo)
        hooks.execute(['foo', 'some', 'other', 'args'])
        self.assertFalse(os.path.exists(config.path))

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

    def test_magic_underscores(self):
        # Juju hook names use hyphens as separators. Python functions use
        # underscores. If explicit names have not been provided, hooks
        # are registered with both the function name and the function
        # name with underscores replaced with hyphens for convenience.
        execs = []
        hooks = hookenv.Hooks()

        @hooks.hook()
        def call_me_maybe():
            execs.append(True)

        hooks.execute(['call-me-maybe'])
        hooks.execute(['call_me_maybe'])
        self.assertEqual(execs, [True, True])

    @patch('charmhelpers.core.hookenv.local_unit')
    def test_gets_service_name(self, _unit):
        _unit.return_value = 'mysql/3'
        self.assertEqual(hookenv.service_name(), 'mysql')

    @patch('charmhelpers.core.hookenv.related_units')
    @patch('charmhelpers.core.hookenv.remote_unit')
    def test_gets_remote_service_name(self, remote_unit, related_units):
        remote_unit.return_value = 'mysql/3'
        related_units.return_value = ['pgsql/0', 'pgsql/1']
        self.assertEqual(hookenv.remote_service_name(), 'mysql')
        self.assertEqual(hookenv.remote_service_name('pgsql:1'), 'pgsql')

    def test_gets_hook_name(self):
        with patch.dict(os.environ, JUJU_HOOK_NAME='hook'):
            self.assertEqual(hookenv.hook_name(), 'hook')
        with patch('sys.argv', ['other-hook']):
            self.assertEqual(hookenv.hook_name(), 'other-hook')

    @patch('subprocess.check_output')
    def test_action_get_with_key(self, check_output):
        action_data = 'bar'
        check_output.return_value = json.dumps(action_data).encode('UTF-8')

        result = hookenv.action_get(key='foo')

        self.assertEqual(result, 'bar')
        check_output.assert_called_with(['action-get', 'foo', '--format=json'])

    @patch('subprocess.check_output')
    def test_action_get_without_key(self, check_output):
        check_output.return_value = json.dumps(dict(foo='bar')).encode('UTF-8')

        result = hookenv.action_get()

        self.assertEqual(result['foo'], 'bar')
        check_output.assert_called_with(['action-get', '--format=json'])

    @patch('subprocess.check_call')
    def test_action_set(self, check_call):
        values = {'foo': 'bar', 'fooz': 'barz'}
        hookenv.action_set(values)
        # The order of the key/value pairs can change, so sort them before test
        called_args = check_call.call_args_list[0][0][0]
        called_args.pop(0)
        called_args.sort()
        self.assertEqual(called_args, ['foo=bar', 'fooz=barz'])

    @patch('subprocess.check_call')
    def test_action_fail(self, check_call):
        message = "Ooops, the action failed"
        hookenv.action_fail(message)
        check_call.assert_called_with(['action-fail', message])

    @patch('charmhelpers.core.hookenv.cmd_exists')
    @patch('subprocess.check_output')
    def test_function_get_with_key(self, check_output, cmd_exists):
        function_data = 'bar'
        check_output.return_value = json.dumps(function_data).encode('UTF-8')
        cmd_exists.return_value = True

        result = hookenv.function_get(key='foo')

        self.assertEqual(result, 'bar')
        check_output.assert_called_with(['function-get', 'foo', '--format=json'])

    @patch('charmhelpers.core.hookenv.cmd_exists')
    @patch('subprocess.check_output')
    def test_function_get_without_key(self, check_output, cmd_exists):
        check_output.return_value = json.dumps(dict(foo='bar')).encode('UTF-8')
        cmd_exists.return_value = True

        result = hookenv.function_get()

        self.assertEqual(result['foo'], 'bar')
        check_output.assert_called_with(['function-get', '--format=json'])

    @patch('subprocess.check_call')
    def test_function_set(self, check_call):
        values = {'foo': 'bar', 'fooz': 'barz'}
        hookenv.function_set(values)
        # The order of the key/value pairs can change, so sort them before test
        called_args = check_call.call_args_list[0][0][0]
        called_args.pop(0)
        called_args.sort()
        self.assertEqual(called_args, ['foo=bar', 'fooz=barz'])

    @patch('charmhelpers.core.hookenv.cmd_exists')
    @patch('subprocess.check_call')
    def test_function_fail(self, check_call, cmd_exists):
        cmd_exists.return_value = True

        message = "Ooops, the function failed"
        hookenv.function_fail(message)
        check_call.assert_called_with(['function-fail', message])

    def test_status_set_invalid_state(self):
        self.assertRaises(ValueError, hookenv.status_set, 'random', 'message')

    def test_status_set_invalid_state_enum(self):

        class RandomEnum(Enum):
            FOO = 1
        self.assertRaises(
            ValueError,
            hookenv.status_set,
            RandomEnum.FOO,
            'message')

    @patch('subprocess.call')
    def test_status(self, call):
        call.return_value = 0
        hookenv.status_set('active', 'Everything is Awesome!')
        call.assert_called_with(['status-set', 'active', 'Everything is Awesome!'])

    @patch('subprocess.call')
    def test_status_enum(self, call):
        call.return_value = 0
        hookenv.status_set(
            hookenv.WORKLOAD_STATES.ACTIVE,
            'Everything is Awesome!')
        call.assert_called_with(['status-set', 'active', 'Everything is Awesome!'])

    @patch('subprocess.call')
    def test_status_app(self, call):
        call.return_value = 0
        hookenv.status_set(
            'active',
            'Everything is Awesome!',
            application=True)
        call.assert_called_with([
            'status-set',
            '--application',
            'active',
            'Everything is Awesome!'])

    @patch('subprocess.call')
    @patch.object(hookenv, 'log')
    def test_status_enoent(self, log, call):
        call.side_effect = OSError(2, 'fail')
        hookenv.status_set('active', 'Everything is Awesome!')
        log.assert_called_with('status-set failed: active Everything is Awesome!', level='INFO')

    @patch('subprocess.call')
    @patch.object(hookenv, 'log')
    def test_status_statuscmd_fail(self, log, call):
        call.side_effect = OSError(3, 'fail')
        self.assertRaises(OSError, hookenv.status_set, 'active', 'msg')
        call.assert_called_with(['status-set', 'active', 'msg'])

    @patch('subprocess.check_output')
    def test_status_get(self, check_output):
        check_output.return_value = json.dumps(
            {"message": "foo",
             "status": "active",
             "status-data": {}}).encode("UTF-8")
        result = hookenv.status_get()
        self.assertEqual(result, ('active', 'foo'))
        check_output.assert_called_with(
            ['status-get', "--format=json", "--include-data"])

    @patch('subprocess.check_output')
    def test_status_get_nostatus(self, check_output):
        check_output.side_effect = OSError(2, 'fail')
        result = hookenv.status_get()
        self.assertEqual(result, ('unknown', ''))

    @patch('subprocess.check_output')
    def test_status_get_status_error(self, check_output):
        check_output.side_effect = OSError(3, 'fail')
        self.assertRaises(OSError, hookenv.status_get)

    @patch('subprocess.check_output')
    @patch('glob.glob')
    def test_juju_version(self, glob, check_output):
        glob.return_value = [sentinel.jujud]
        check_output.return_value = '1.23.3.1-trusty-amd64\n'
        self.assertEqual(hookenv.juju_version(), '1.23.3.1-trusty-amd64')
        # Per https://bugs.launchpad.net/juju-core/+bug/1455368/comments/1
        glob.assert_called_once_with('/var/lib/juju/tools/machine-*/jujud')
        check_output.assert_called_once_with([sentinel.jujud, 'version'],
                                             universal_newlines=True)

    @patch('charmhelpers.core.hookenv.juju_version')
    def test_has_juju_version(self, juju_version):
        juju_version.return_value = '1.23.1.2.3.4.5-with-a-cherry-on-top.amd64'
        self.assertTrue(hookenv.has_juju_version('1.23'))
        self.assertTrue(hookenv.has_juju_version('1.23.1'))
        self.assertTrue(hookenv.has_juju_version('1.23.1.1'))
        self.assertFalse(hookenv.has_juju_version('1.23.2.1'))
        self.assertFalse(hookenv.has_juju_version('1.24'))

        juju_version.return_value = '1.24-beta5.1-trusty-amd64'
        self.assertTrue(hookenv.has_juju_version('1.23'))
        self.assertTrue(hookenv.has_juju_version('1.24'))  # Better if this was false!
        self.assertTrue(hookenv.has_juju_version('1.24-beta5'))
        self.assertTrue(hookenv.has_juju_version('1.24-beta5.1'))
        self.assertFalse(hookenv.has_juju_version('1.25'))
        self.assertTrue(hookenv.has_juju_version('1.18-backport6'))

    @patch.object(hookenv, 'relation_to_role_and_interface')
    def test_relation_to_interface(self, rtri):
        rtri.return_value = (None, 'foo')
        self.assertEqual(hookenv.relation_to_interface('rel'), 'foo')

    @patch.object(hookenv, 'metadata')
    def test_relation_to_role_and_interface(self, metadata):
        metadata.return_value = {
            'provides': {
                'pro-rel': {
                    'interface': 'pro-int',
                },
                'pro-rel2': {
                    'interface': 'pro-int',
                },
            },
            'requires': {
                'req-rel': {
                    'interface': 'req-int',
                },
            },
            'peers': {
                'pee-rel': {
                    'interface': 'pee-int',
                },
            },
        }
        rtri = hookenv.relation_to_role_and_interface
        self.assertEqual(rtri('pro-rel'), ('provides', 'pro-int'))
        self.assertEqual(rtri('req-rel'), ('requires', 'req-int'))
        self.assertEqual(rtri('pee-rel'), ('peers', 'pee-int'))

    @patch.object(hookenv, 'metadata')
    def test_role_and_interface_to_relations(self, metadata):
        metadata.return_value = {
            'provides': {
                'pro-rel': {
                    'interface': 'pro-int',
                },
                'pro-rel2': {
                    'interface': 'pro-int',
                },
            },
            'requires': {
                'req-rel': {
                    'interface': 'int',
                },
            },
            'peers': {
                'pee-rel': {
                    'interface': 'int',
                },
            },
        }
        ritr = hookenv.role_and_interface_to_relations
        assertItemsEqual = getattr(self, 'assertItemsEqual', getattr(self, 'assertCountEqual', None))
        assertItemsEqual(ritr('provides', 'pro-int'), ['pro-rel', 'pro-rel2'])
        assertItemsEqual(ritr('requires', 'int'), ['req-rel'])
        assertItemsEqual(ritr('peers', 'int'), ['pee-rel'])

    @patch.object(hookenv, 'metadata')
    def test_interface_to_relations(self, metadata):
        metadata.return_value = {
            'provides': {
                'pro-rel': {
                    'interface': 'pro-int',
                },
                'pro-rel2': {
                    'interface': 'pro-int',
                },
            },
            'requires': {
                'req-rel': {
                    'interface': 'req-int',
                },
            },
            'peers': {
                'pee-rel': {
                    'interface': 'pee-int',
                },
            },
        }
        itr = hookenv.interface_to_relations
        assertItemsEqual = getattr(self, 'assertItemsEqual', getattr(self, 'assertCountEqual', None))
        assertItemsEqual(itr('pro-int'), ['pro-rel', 'pro-rel2'])
        assertItemsEqual(itr('req-int'), ['req-rel'])
        assertItemsEqual(itr('pee-int'), ['pee-rel'])

    def test_action_name(self):
        with patch.dict('os.environ', JUJU_ACTION_NAME='action-jack'):
            self.assertEqual(hookenv.action_name(), 'action-jack')

    def test_action_uuid(self):
        with patch.dict('os.environ', JUJU_ACTION_UUID='action-jack'):
            self.assertEqual(hookenv.action_uuid(), 'action-jack')

    def test_action_tag(self):
        with patch.dict('os.environ', JUJU_ACTION_TAG='action-jack'):
            self.assertEqual(hookenv.action_tag(), 'action-jack')

    @patch('subprocess.check_output')
    def test_storage_list(self, check_output):
        ids = ['data/0', 'data/1', 'data/2']
        check_output.return_value = json.dumps(ids).encode('UTF-8')

        storage_name = 'arbitrary'
        result = hookenv.storage_list(storage_name)

        self.assertEqual(result, ids)
        check_output.assert_called_with(['storage-list', '--format=json',
                                         storage_name])

    @patch('subprocess.check_output')
    def test_storage_list_notexist(self, check_output):
        import errno
        e = OSError()
        e.errno = errno.ENOENT
        check_output.side_effect = e

        result = hookenv.storage_list()

        self.assertEqual(result, [])
        check_output.assert_called_with(['storage-list', '--format=json'])

    @patch('subprocess.check_output')
    def test_storage_get_notexist(self, check_output):
        # storage_get does not catch ENOENT, because there's no reason why you
        # should be calling storage_get except from a storage hook, or with
        # the result of storage_list (which will return [] as shown above).

        import errno
        e = OSError()
        e.errno = errno.ENOENT
        check_output.side_effect = e
        self.assertRaises(OSError, hookenv.storage_get)

    @patch('subprocess.check_output')
    def test_storage_get(self, check_output):
        expect = {
            'location': '/dev/sda',
            'kind': 'block',
        }
        check_output.return_value = json.dumps(expect).encode('UTF-8')

        result = hookenv.storage_get()

        self.assertEqual(result, expect)
        check_output.assert_called_with(['storage-get', '--format=json'])

    @patch('subprocess.check_output')
    def test_storage_get_attr(self, check_output):
        expect = '/dev/sda'
        check_output.return_value = json.dumps(expect).encode('UTF-8')

        attribute = 'location'
        result = hookenv.storage_get(attribute)

        self.assertEqual(result, expect)
        check_output.assert_called_with(['storage-get', '--format=json',
                                         attribute])

    @patch('subprocess.check_output')
    def test_storage_get_with_id(self, check_output):
        expect = {
            'location': '/dev/sda',
            'kind': 'block',
        }
        check_output.return_value = json.dumps(expect).encode('UTF-8')

        storage_id = 'data/0'
        result = hookenv.storage_get(storage_id=storage_id)

        self.assertEqual(result, expect)
        check_output.assert_called_with(['storage-get', '--format=json',
                                         '-s', storage_id])

    @patch('subprocess.check_output')
    def test_network_get_primary(self, check_output):
        """Ensure that network-get is called correctly and output is returned"""
        check_output.return_value = b'192.168.22.1'
        ip = hookenv.network_get_primary_address('mybinding')
        check_output.assert_called_with(
            ['network-get', '--primary-address', 'mybinding'], stderr=-2)
        self.assertEqual(ip, '192.168.22.1')

    @patch('subprocess.check_output')
    def test_network_get_primary_unsupported(self, check_output):
        """Ensure that NotImplementedError is thrown when run on Juju < 2.0"""
        check_output.side_effect = OSError(2, 'network-get')
        self.assertRaises(NotImplementedError, hookenv.network_get_primary_address,
                          'mybinding')

    @patch('subprocess.check_output')
    def test_network_get_primary_no_binding_found(self, check_output):
        """Ensure that NotImplementedError when no binding is found"""
        check_output.side_effect = CalledProcessError(
            1, 'network-get',
            output='no network config found for binding'.encode('UTF-8'))
        self.assertRaises(hookenv.NoNetworkBinding,
                          hookenv.network_get_primary_address,
                          'doesnotexist')
        check_output.assert_called_with(
            ['network-get', '--primary-address', 'doesnotexist'], stderr=-2)

    @patch('subprocess.check_output')
    def test_network_get_primary_other_exception(self, check_output):
        """Ensure that CalledProcessError still thrown when not
        a missing binding"""
        check_output.side_effect = CalledProcessError(
            1, 'network-get',
            output='any other message'.encode('UTF-8'))
        self.assertRaises(CalledProcessError,
                          hookenv.network_get_primary_address,
                          'mybinding')

    @patch('charmhelpers.core.hookenv.juju_version')
    @patch('subprocess.check_output')
    def test_network_get(self, check_output, juju_version):
        """Ensure that network-get is called correctly"""
        juju_version.return_value = '2.2.0'
        check_output.return_value = b'result'
        hookenv.network_get('endpoint')
        check_output.assert_called_with(
            ['network-get', 'endpoint', '--format', 'yaml'], stderr=-2)

    @patch('charmhelpers.core.hookenv.juju_version')
    @patch('subprocess.check_output')
    def test_network_get_primary_required(self, check_output, juju_version):
        """Ensure that NotImplementedError is thrown with Juju < 2.2.0"""
        check_output.return_value = b'result'

        juju_version.return_value = '2.1.4'
        self.assertRaises(NotImplementedError, hookenv.network_get, 'binding')
        juju_version.return_value = '2.2.0'
        self.assertEquals(hookenv.network_get('endpoint'), 'result')

    @patch('charmhelpers.core.hookenv.juju_version')
    @patch('subprocess.check_output')
    def test_network_get_relation_bound(self, check_output, juju_version):
        """Ensure that network-get supports relation context, requires Juju 2.3"""
        juju_version.return_value = '2.3.0'
        check_output.return_value = b'result'
        hookenv.network_get('endpoint', 'db')
        check_output.assert_called_with(
            ['network-get', 'endpoint', '--format', 'yaml', '-r', 'db'],
            stderr=-2)
        juju_version.return_value = '2.2.8'
        self.assertRaises(NotImplementedError, hookenv.network_get, 'endpoint', 'db')

    @patch('charmhelpers.core.hookenv.juju_version')
    @patch('subprocess.check_output')
    def test_network_get_parses_yaml(self, check_output, juju_version):
        """network-get returns loaded YAML output."""
        juju_version.return_value = '2.3.0'
        check_output.return_value = b"""
bind-addresses:
- macaddress: ""
  interfacename: ""
  addresses:
    - address: 10.136.107.33
      cidr: ""
ingress-addresses:
- 10.136.107.33
        """
        ip = hookenv.network_get('mybinding')
        self.assertEqual(len(ip['bind-addresses']), 1)
        self.assertEqual(ip['ingress-addresses'], ['10.136.107.33'])

    @patch('subprocess.check_call')
    def test_add_metric(self, check_call_):
        hookenv.add_metric(flips='1.5', flops='2.1')
        hookenv.add_metric('juju-units=6')
        hookenv.add_metric('foo-bar=3.333', 'baz-quux=8', users='2')
        calls = [
            call(['add-metric', 'flips=1.5', 'flops=2.1']),
            call(['add-metric', 'juju-units=6']),
            call(['add-metric', 'baz-quux=8', 'foo-bar=3.333', 'users=2']),
        ]
        check_call_.assert_has_calls(calls)

    @patch('subprocess.check_call')
    @patch.object(hookenv, 'log')
    def test_add_metric_enoent(self, log, _check_call):
        _check_call.side_effect = OSError(2, 'fail')
        hookenv.add_metric(flips='1')
        log.assert_called_with('add-metric failed: flips=1', level='INFO')

    @patch('charmhelpers.core.hookenv.os')
    def test_meter_status(self, os_):
        os_.environ = {
            'JUJU_METER_STATUS': 'GREEN',
            'JUJU_METER_INFO': 'all good',
        }
        self.assertEqual(hookenv.meter_status(), 'GREEN')
        self.assertEqual(hookenv.meter_info(), 'all good')

    @patch.object(hookenv, 'related_units')
    @patch.object(hookenv, 'relation_ids')
    def test_iter_units_for_relation_name(self, relation_ids, related_units):
        relation_ids.return_value = ['rel:1']
        related_units.return_value = ['unit/0', 'unit/1', 'unit/2']
        expected = [('rel:1', 'unit/0'),
                    ('rel:1', 'unit/1'),
                    ('rel:1', 'unit/2')]
        related_units_data = [
            (u.rid, u.unit)
            for u in hookenv.iter_units_for_relation_name('rel')]
        self.assertEqual(expected, related_units_data)

    @patch.object(hookenv, 'relation_get')
    def test_ingress_address(self, relation_get):
        """Ensure ingress_address returns the ingress-address when available
        and returns the private-address when not.
        """
        _with_ingress = {'egress-subnets': '10.5.0.23/32',
                         'ingress-address': '10.5.0.23',
                         'private-address': '172.16.5.10'}

        _without_ingress = {'private-address': '172.16.5.10'}

        # Return the ingress-address
        relation_get.return_value = _with_ingress
        self.assertEqual(hookenv.ingress_address(rid='test:1', unit='unit/1'),
                         '10.5.0.23')
        relation_get.assert_called_with(rid='test:1', unit='unit/1')
        # Return the private-address
        relation_get.return_value = _without_ingress
        self.assertEqual(hookenv.ingress_address(rid='test:1'),
                         '172.16.5.10')

    @patch.object(hookenv, 'relation_get')
    def test_egress_subnets(self, relation_get):
        """Ensure egress_subnets returns the decoded egress-subnets when available
        and falls back correctly when not.
        """
        d = {'egress-subnets': '10.5.0.23/32,2001::F00F/64',
             'ingress-address': '10.5.0.23',
             'private-address': '2001::D0:F00D'}

        # Return the egress-subnets
        relation_get.return_value = d
        self.assertEqual(hookenv.egress_subnets(rid='test:1', unit='unit/1'),
                         ['10.5.0.23/32', '2001::F00F/64'])
        relation_get.assert_called_with(rid='test:1', unit='unit/1')

        # Return the ingress-address
        del d['egress-subnets']
        self.assertEqual(hookenv.egress_subnets(), ['10.5.0.23/32'])

        # Return the private-address
        del d['ingress-address']
        self.assertEqual(hookenv.egress_subnets(), ['2001::D0:F00D/128'])

    @patch('charmhelpers.core.hookenv.local_unit')
    @patch('charmhelpers.core.hookenv.goal_state')
    @patch('charmhelpers.core.hookenv.has_juju_version')
    def test_unit_doomed(self, has_juju_version, goal_state, local_unit):
        # We need to test for a minimum patch level, or we risk
        # data loss by returning bogus results with Juju 2.4.0
        has_juju_version.return_value = False
        self.assertRaises(NotImplementedError, hookenv.unit_doomed)
        has_juju_version.assertCalledOnceWith("2.4.1")
        has_juju_version.return_value = True

        goal_state.return_value = json.loads('''
                                             {
                                                "units": {
                                                    "postgresql/0": {
                                                        "status": "dying",
                                                        "since": "2018-07-30 10:01:06Z"
                                                    },
                                                    "postgresql/1": {
                                                        "status": "active",
                                                        "since": "2018-07-30 10:22:39Z"
                                                    }
                                                },
                                                "relations": {}
                                             }
                                             ''')
        self.assertTrue(hookenv.unit_doomed('postgresql/0'))   # unit removed, status "dying"
        self.assertFalse(hookenv.unit_doomed('postgresql/1'))  # unit exists, status "active", maybe other states
        self.assertTrue(hookenv.unit_doomed('postgresql/2'))   # unit does not exist

        local_unit.return_value = 'postgresql/0'
        self.assertTrue(hookenv.unit_doomed())

    def test_contains_addr_range(self):
        # Contains cidr
        self.assertTrue(hookenv._contains_range("192.168.1/20"))
        self.assertTrue(hookenv._contains_range("192.168.0/24"))
        self.assertTrue(
            hookenv._contains_range("10.40.50.1,192.168.1/20,10.56.78.9"))
        self.assertTrue(hookenv._contains_range("192.168.22/24"))
        self.assertTrue(hookenv._contains_range("2001:db8::/32"))
        self.assertTrue(hookenv._contains_range("*.foo.com"))
        self.assertTrue(hookenv._contains_range(".foo.com"))
        self.assertTrue(
            hookenv._contains_range("192.168.1.20,.foo.com"))
        self.assertTrue(
            hookenv._contains_range("192.168.1.20,  .foo.com"))
        self.assertTrue(
            hookenv._contains_range("192.168.1.20,*.foo.com"))

        # Doesn't contain cidr
        self.assertFalse(hookenv._contains_range("192.168.1"))
        self.assertFalse(hookenv._contains_range("192.168.145"))
        self.assertFalse(hookenv._contains_range("192.16.14"))
