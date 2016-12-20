import os
import mock
import unittest
import uuid
from charmhelpers.core import hookenv
from charmhelpers.core import host
from charmhelpers.core import services
from functools import partial


class TestServiceManager(unittest.TestCase):
    def setUp(self):
        self.pcharm_dir = mock.patch.object(hookenv, 'charm_dir')
        self.mcharm_dir = self.pcharm_dir.start()
        self.mcharm_dir.return_value = 'charm_dir'

    def tearDown(self):
        self.pcharm_dir.stop()

    def test_register(self):
        manager = services.ServiceManager([
            {'service': 'service1',
             'foo': 'bar'},
            {'service': 'service2',
             'qux': 'baz'},
        ])
        self.assertEqual(manager.services, {
            'service1': {'service': 'service1',
                         'foo': 'bar'},
            'service2': {'service': 'service2',
                         'qux': 'baz'},
        })

    def test_register_preserves_order(self):
        service_list = [dict(service='a'), dict(service='b')]

        # Test that the services list order is preserved by checking
        # both forwards and backwards - only one of these will be
        # dictionary order, and if both work we know order is being
        # preserved.
        manager = services.ServiceManager(service_list)
        self.assertEqual(list(manager.services.keys()), ['a', 'b'])
        manager = services.ServiceManager(reversed(service_list))
        self.assertEqual(list(manager.services.keys()), ['b', 'a'])

    @mock.patch.object(services.ServiceManager, 'reconfigure_services')
    @mock.patch.object(services.ServiceManager, 'stop_services')
    @mock.patch.object(hookenv, 'hook_name')
    @mock.patch.object(hookenv, 'config')
    def test_manage_stop(self, config, hook_name, stop_services, reconfigure_services):
        manager = services.ServiceManager()
        hook_name.return_value = 'stop'
        manager.manage()
        stop_services.assert_called_once_with()
        assert not reconfigure_services.called

    @mock.patch.object(services.ServiceManager, 'provide_data')
    @mock.patch.object(services.ServiceManager, 'reconfigure_services')
    @mock.patch.object(services.ServiceManager, 'stop_services')
    @mock.patch.object(hookenv, 'hook_name')
    @mock.patch.object(hookenv, 'config')
    def test_manage_other(self, config, hook_name, stop_services, reconfigure_services, provide_data):
        manager = services.ServiceManager()
        hook_name.return_value = 'config-changed'
        manager.manage()
        assert not stop_services.called
        reconfigure_services.assert_called_once_with()
        provide_data.assert_called_once_with()

    def test_manage_calls_atstart(self):
        cb = mock.MagicMock()
        hookenv.atstart(cb)
        manager = services.ServiceManager()
        manager.manage()
        self.assertTrue(cb.called)

    def test_manage_calls_atexit(self):
        cb = mock.MagicMock()
        hookenv.atexit(cb)
        manager = services.ServiceManager()
        manager.manage()
        self.assertTrue(cb.called)

    @mock.patch.object(hookenv, 'config')
    def test_manage_config_not_saved(self, config):
        config = config.return_value
        config.implicit_save = False
        manager = services.ServiceManager()
        manager.manage()
        self.assertFalse(config.save.called)

    @mock.patch.object(services.ServiceManager, 'save_ready')
    @mock.patch.object(services.ServiceManager, 'fire_event')
    @mock.patch.object(services.ServiceManager, 'is_ready')
    def test_reconfigure_ready(self, is_ready, fire_event, save_ready):
        manager = services.ServiceManager([
            {'service': 'service1'}, {'service': 'service2'}])
        is_ready.return_value = True
        manager.reconfigure_services()
        is_ready.assert_has_calls([
            mock.call('service1'),
            mock.call('service2'),
        ], any_order=True)
        fire_event.assert_has_calls([
            mock.call('data_ready', 'service1'),
            mock.call('start', 'service1', default=[
                services.service_restart,
                services.manage_ports]),
        ], any_order=False)
        fire_event.assert_has_calls([
            mock.call('data_ready', 'service2'),
            mock.call('start', 'service2', default=[
                services.service_restart,
                services.manage_ports]),
        ], any_order=False)
        save_ready.assert_has_calls([
            mock.call('service1'),
            mock.call('service2'),
        ], any_order=True)

    @mock.patch.object(services.ServiceManager, 'save_ready')
    @mock.patch.object(services.ServiceManager, 'fire_event')
    @mock.patch.object(services.ServiceManager, 'is_ready')
    def test_reconfigure_ready_list(self, is_ready, fire_event, save_ready):
        manager = services.ServiceManager([
            {'service': 'service1'}, {'service': 'service2'}])
        is_ready.return_value = True
        manager.reconfigure_services('service3', 'service4')
        self.assertEqual(is_ready.call_args_list, [
            mock.call('service3'),
            mock.call('service4'),
        ])
        self.assertEqual(fire_event.call_args_list, [
            mock.call('data_ready', 'service3'),
            mock.call('start', 'service3', default=[
                services.service_restart,
                services.open_ports]),
            mock.call('data_ready', 'service4'),
            mock.call('start', 'service4', default=[
                services.service_restart,
                services.open_ports]),
        ])
        self.assertEqual(save_ready.call_args_list, [
            mock.call('service3'),
            mock.call('service4'),
        ])

    @mock.patch.object(services.ServiceManager, 'save_lost')
    @mock.patch.object(services.ServiceManager, 'fire_event')
    @mock.patch.object(services.ServiceManager, 'was_ready')
    @mock.patch.object(services.ServiceManager, 'is_ready')
    def test_reconfigure_not_ready(self, is_ready, was_ready, fire_event, save_lost):
        manager = services.ServiceManager([
            {'service': 'service1'}, {'service': 'service2'}])
        is_ready.return_value = False
        was_ready.return_value = False
        manager.reconfigure_services()
        is_ready.assert_has_calls([
            mock.call('service1'),
            mock.call('service2'),
        ], any_order=True)
        fire_event.assert_has_calls([
            mock.call('stop', 'service1', default=[
                services.close_ports,
                services.service_stop]),
            mock.call('stop', 'service2', default=[
                services.close_ports,
                services.service_stop]),
        ], any_order=True)
        save_lost.assert_has_calls([
            mock.call('service1'),
            mock.call('service2'),
        ], any_order=True)

    @mock.patch.object(services.ServiceManager, 'save_lost')
    @mock.patch.object(services.ServiceManager, 'fire_event')
    @mock.patch.object(services.ServiceManager, 'was_ready')
    @mock.patch.object(services.ServiceManager, 'is_ready')
    def test_reconfigure_no_longer_ready(self, is_ready, was_ready, fire_event, save_lost):
        manager = services.ServiceManager([
            {'service': 'service1'}, {'service': 'service2'}])
        is_ready.return_value = False
        was_ready.return_value = True
        manager.reconfigure_services()
        is_ready.assert_has_calls([
            mock.call('service1'),
            mock.call('service2'),
        ], any_order=True)
        fire_event.assert_has_calls([
            mock.call('data_lost', 'service1'),
            mock.call('stop', 'service1', default=[
                services.close_ports,
                services.service_stop]),
        ], any_order=False)
        fire_event.assert_has_calls([
            mock.call('data_lost', 'service2'),
            mock.call('stop', 'service2', default=[
                services.close_ports,
                services.service_stop]),
        ], any_order=False)
        save_lost.assert_has_calls([
            mock.call('service1'),
            mock.call('service2'),
        ], any_order=True)

    @mock.patch.object(services.ServiceManager, 'fire_event')
    def test_stop_services(self, fire_event):
        manager = services.ServiceManager([
            {'service': 'service1'}, {'service': 'service2'}])
        manager.stop_services()
        fire_event.assert_has_calls([
            mock.call('stop', 'service1', default=[
                services.close_ports,
                services.service_stop]),
            mock.call('stop', 'service2', default=[
                services.close_ports,
                services.service_stop]),
        ], any_order=True)

    @mock.patch.object(services.ServiceManager, 'fire_event')
    def test_stop_services_list(self, fire_event):
        manager = services.ServiceManager([
            {'service': 'service1'}, {'service': 'service2'}])
        manager.stop_services('service3', 'service4')
        self.assertEqual(fire_event.call_args_list, [
            mock.call('stop', 'service3', default=[
                services.close_ports,
                services.service_stop]),
            mock.call('stop', 'service4', default=[
                services.close_ports,
                services.service_stop]),
        ])

    def test_get_service(self):
        service = {'service': 'test', 'test': 'test_service'}
        manager = services.ServiceManager([service])
        self.assertEqual(manager.get_service('test'), service)

    def test_get_service_not_registered(self):
        service = {'service': 'test', 'test': 'test_service'}
        manager = services.ServiceManager([service])
        self.assertRaises(KeyError, manager.get_service, 'foo')

    @mock.patch.object(services.ServiceManager, 'get_service')
    def test_fire_event_default(self, get_service):
        get_service.return_value = {}
        cb = mock.Mock()
        manager = services.ServiceManager()
        manager.fire_event('event', 'service', cb)
        cb.assert_called_once_with('service')

    @mock.patch.object(services.ServiceManager, 'get_service')
    def test_fire_event_default_list(self, get_service):
        get_service.return_value = {}
        cb = mock.Mock()
        manager = services.ServiceManager()
        manager.fire_event('event', 'service', [cb])
        cb.assert_called_once_with('service')

    @mock.patch.object(services.ServiceManager, 'get_service')
    def test_fire_event_simple_callback(self, get_service):
        cb = mock.Mock()
        dcb = mock.Mock()
        get_service.return_value = {'event': cb}
        manager = services.ServiceManager()
        manager.fire_event('event', 'service', dcb)
        assert not dcb.called
        cb.assert_called_once_with('service')

    @mock.patch.object(services.ServiceManager, 'get_service')
    def test_fire_event_simple_callback_list(self, get_service):
        cb = mock.Mock()
        dcb = mock.Mock()
        get_service.return_value = {'event': [cb]}
        manager = services.ServiceManager()
        manager.fire_event('event', 'service', dcb)
        assert not dcb.called
        cb.assert_called_once_with('service')

    @mock.patch.object(services.ManagerCallback, '__call__')
    @mock.patch.object(services.ServiceManager, 'get_service')
    def test_fire_event_manager_callback(self, get_service, mcall):
        cb = services.ManagerCallback()
        dcb = mock.Mock()
        get_service.return_value = {'event': cb}
        manager = services.ServiceManager()
        manager.fire_event('event', 'service', dcb)
        assert not dcb.called
        mcall.assert_called_once_with(manager, 'service', 'event')

    @mock.patch.object(services.ManagerCallback, '__call__')
    @mock.patch.object(services.ServiceManager, 'get_service')
    def test_fire_event_manager_callback_list(self, get_service, mcall):
        cb = services.ManagerCallback()
        dcb = mock.Mock()
        get_service.return_value = {'event': [cb]}
        manager = services.ServiceManager()
        manager.fire_event('event', 'service', dcb)
        assert not dcb.called
        mcall.assert_called_once_with(manager, 'service', 'event')

    @mock.patch.object(services.ServiceManager, 'get_service')
    def test_is_ready(self, get_service):
        get_service.side_effect = [
            {},
            {'required_data': [True]},
            {'required_data': [False]},
            {'required_data': [True, False]},
        ]
        manager = services.ServiceManager()
        assert manager.is_ready('foo')
        assert manager.is_ready('bar')
        assert not manager.is_ready('foo')
        assert not manager.is_ready('foo')
        get_service.assert_has_calls([mock.call('foo'), mock.call('bar')])

    def test_load_ready_file_short_circuit(self):
        manager = services.ServiceManager()
        manager._ready = 'foo'
        manager._load_ready_file()
        self.assertEqual(manager._ready, 'foo')

    @mock.patch('os.path.exists')
    @mock.patch.object(services.base, 'open', create=True)
    def test_load_ready_file_new(self, mopen, exists):
        manager = services.ServiceManager()
        exists.return_value = False
        manager._load_ready_file()
        self.assertEqual(manager._ready, set())
        assert not mopen.called

    @mock.patch('json.load')
    @mock.patch('os.path.exists')
    @mock.patch.object(services.base, 'open', create=True)
    def test_load_ready_file(self, mopen, exists, jload):
        manager = services.ServiceManager()
        exists.return_value = True
        jload.return_value = ['bar']
        manager._load_ready_file()
        self.assertEqual(manager._ready, set(['bar']))
        exists.assert_called_once_with('charm_dir/READY-SERVICES.json')
        mopen.assert_called_once_with('charm_dir/READY-SERVICES.json')

    @mock.patch('json.dump')
    @mock.patch.object(services.base, 'open', create=True)
    def test_save_ready_file(self, mopen, jdump):
        manager = services.ServiceManager()
        manager._save_ready_file()
        assert not mopen.called
        manager._ready = set(['foo'])
        manager._save_ready_file()
        mopen.assert_called_once_with('charm_dir/READY-SERVICES.json', 'w')
        jdump.assert_called_once_with(['foo'], mopen.return_value.__enter__())

    @mock.patch.object(services.base.ServiceManager, '_save_ready_file')
    @mock.patch.object(services.base.ServiceManager, '_load_ready_file')
    def test_save_ready(self, _lrf, _srf):
        manager = services.ServiceManager()
        manager._ready = set(['foo'])
        manager.save_ready('bar')
        _lrf.assert_called_once_with()
        self.assertEqual(manager._ready, set(['foo', 'bar']))
        _srf.assert_called_once_with()

    @mock.patch.object(services.base.ServiceManager, '_save_ready_file')
    @mock.patch.object(services.base.ServiceManager, '_load_ready_file')
    def test_save_lost(self, _lrf, _srf):
        manager = services.ServiceManager()
        manager._ready = set(['foo', 'bar'])
        manager.save_lost('bar')
        _lrf.assert_called_once_with()
        self.assertEqual(manager._ready, set(['foo']))
        _srf.assert_called_once_with()
        manager.save_lost('bar')
        self.assertEqual(manager._ready, set(['foo']))

    @mock.patch.object(services.base.ServiceManager, '_save_ready_file')
    @mock.patch.object(services.base.ServiceManager, '_load_ready_file')
    def test_was_ready(self, _lrf, _srf):
        manager = services.ServiceManager()
        manager._ready = set()
        manager.save_ready('foo')
        manager.save_ready('bar')
        assert manager.was_ready('foo')
        assert manager.was_ready('bar')
        manager.save_lost('bar')
        assert manager.was_ready('foo')
        assert not manager.was_ready('bar')

    @mock.patch.object(services.base.hookenv, 'relation_set')
    @mock.patch.object(services.base.hookenv, 'related_units')
    @mock.patch.object(services.base.hookenv, 'relation_ids')
    def test_provide_data_no_match(self, relation_ids, related_units, relation_set):
        provider = mock.Mock()
        provider.name = 'provided'
        manager = services.ServiceManager([
            {'service': 'service', 'provided_data': [provider]}
        ])
        relation_ids.return_value = []
        manager.provide_data()
        assert not provider.provide_data.called
        relation_ids.assert_called_once_with('provided')

    @mock.patch.object(services.base.hookenv, 'relation_set')
    @mock.patch.object(services.base.hookenv, 'related_units')
    @mock.patch.object(services.base.hookenv, 'relation_ids')
    def test_provide_data_not_ready(self, relation_ids, related_units, relation_set):
        provider = mock.Mock()
        provider.name = 'provided'
        pd = mock.Mock()
        data = pd.return_value = {'data': True}
        provider.provide_data = lambda remote_service, service_ready: pd(remote_service, service_ready)
        manager = services.ServiceManager([
            {'service': 'service', 'provided_data': [provider]}
        ])
        manager.is_ready = mock.Mock(return_value=False)
        relation_ids.return_value = ['relid']
        related_units.return_value = ['service/0']
        manager.provide_data()
        relation_set.assert_called_once_with('relid', data)
        pd.assert_called_once_with('service', False)

    @mock.patch.object(services.base.hookenv, 'relation_set')
    @mock.patch.object(services.base.hookenv, 'related_units')
    @mock.patch.object(services.base.hookenv, 'relation_ids')
    def test_provide_data_ready(self, relation_ids, related_units, relation_set):
        provider = mock.Mock()
        provider.name = 'provided'
        pd = mock.Mock()
        data = pd.return_value = {'data': True}
        provider.provide_data = lambda remote_service, service_ready: pd(remote_service, service_ready)
        manager = services.ServiceManager([
            {'service': 'service', 'provided_data': [provider]}
        ])
        manager.is_ready = mock.Mock(return_value=True)
        relation_ids.return_value = ['relid']
        related_units.return_value = ['service/0']
        manager.provide_data()
        relation_set.assert_called_once_with('relid', data)
        pd.assert_called_once_with('service', True)


class TestRelationContext(unittest.TestCase):
    def setUp(self):
        self.phookenv = mock.patch.object(services.helpers, 'hookenv')
        self.mhookenv = self.phookenv.start()
        self.mhookenv.relation_ids.return_value = []
        self.context = services.RelationContext()
        self.context.name = 'http'
        self.context.interface = 'http'
        self.context.required_keys = ['foo', 'bar']
        self.mhookenv.reset_mock()

    def tearDown(self):
        self.phookenv.stop()

    def test_no_relations(self):
        self.context.get_data()
        self.assertFalse(self.context.is_ready())
        self.assertEqual(self.context, {})
        self.mhookenv.relation_ids.assert_called_once_with('http')

    def test_no_units(self):
        self.mhookenv.relation_ids.return_value = ['nginx']
        self.mhookenv.related_units.return_value = []
        self.context.get_data()
        self.assertFalse(self.context.is_ready())
        self.assertEqual(self.context, {'http': []})

    def test_incomplete(self):
        self.mhookenv.relation_ids.return_value = ['nginx', 'apache']
        self.mhookenv.related_units.side_effect = lambda i: [i + '/0']
        self.mhookenv.relation_get.side_effect = [{}, {'foo': '1'}]
        self.context.get_data()
        self.assertFalse(bool(self.context))
        self.assertEqual(self.mhookenv.relation_get.call_args_list, [
            mock.call(rid='apache', unit='apache/0'),
            mock.call(rid='nginx', unit='nginx/0'),
        ])

    def test_complete(self):
        self.mhookenv.relation_ids.return_value = ['nginx', 'apache', 'tomcat']
        self.mhookenv.related_units.side_effect = lambda i: [i + '/0']
        self.mhookenv.relation_get.side_effect = [{'foo': '1'}, {'foo': '2', 'bar': '3'}, {}]
        self.context.get_data()
        self.assertTrue(self.context.is_ready())
        self.assertEqual(self.context, {'http': [
            {
                'foo': '2',
                'bar': '3',
            },
        ]})
        self.mhookenv.relation_ids.assert_called_with('http')
        self.assertEqual(self.mhookenv.relation_get.call_args_list, [
            mock.call(rid='apache', unit='apache/0'),
            mock.call(rid='nginx', unit='nginx/0'),
            mock.call(rid='tomcat', unit='tomcat/0'),
        ])

    def test_provide(self):
        self.assertEqual(self.context.provide_data(), {})


class TestHttpRelation(unittest.TestCase):
    def setUp(self):
        self.phookenv = mock.patch.object(services.helpers, 'hookenv')
        self.mhookenv = self.phookenv.start()

        self.context = services.helpers.HttpRelation()

    def tearDown(self):
        self.phookenv.stop()

    def test_provide_data(self):
        self.mhookenv.unit_get.return_value = "127.0.0.1"
        self.assertEqual(self.context.provide_data(), {
            'host': "127.0.0.1",
            'port': 80,
        })

    def test_complete(self):
        self.mhookenv.relation_ids.return_value = ['website']
        self.mhookenv.related_units.side_effect = lambda i: [i + '/0']
        self.mhookenv.relation_get.side_effect = [{'host': '127.0.0.2',
                                                   'port': 8080}]
        self.context.get_data()
        self.assertTrue(self.context.is_ready())
        self.assertEqual(self.context, {'website': [
            {
                'host': '127.0.0.2',
                'port': 8080,
            },
        ]})

        self.mhookenv.relation_ids.assert_called_with('website')
        self.assertEqual(self.mhookenv.relation_get.call_args_list, [
            mock.call(rid='website', unit='website/0'),
        ])


class TestMysqlRelation(unittest.TestCase):

    def setUp(self):
        self.phookenv = mock.patch.object(services.helpers, 'hookenv')
        self.mhookenv = self.phookenv.start()

        self.context = services.helpers.MysqlRelation()

    def tearDown(self):
        self.phookenv.stop()

    def test_complete(self):
        self.mhookenv.relation_ids.return_value = ['db']
        self.mhookenv.related_units.side_effect = lambda i: [i + '/0']
        self.mhookenv.relation_get.side_effect = [{'host': '127.0.0.2',
                                                   'user': 'mysql',
                                                   'password': 'mysql',
                                                   'database': 'mysql',
                                                   }]
        self.context.get_data()
        self.assertTrue(self.context.is_ready())
        self.assertEqual(self.context, {'db': [
            {
                'host': '127.0.0.2',
                'user': 'mysql',
                'password': 'mysql',
                'database': 'mysql',
            },
        ]})

        self.mhookenv.relation_ids.assert_called_with('db')
        self.assertEqual(self.mhookenv.relation_get.call_args_list, [
            mock.call(rid='db', unit='db/0'),
        ])


class TestRequiredConfig(unittest.TestCase):
    def setUp(self):
        self.options = {
            'options': {
                'option1': {
                    'type': 'string',
                    'description': 'First option',
                },
                'option2': {
                    'type': 'int',
                    'default': 0,
                    'description': 'Second option',
                },
            },
        }
        self.config = {
            'option1': None,
            'option2': 0,
        }
        self._pyaml = mock.patch.object(services.helpers, 'yaml')
        self.myaml = self._pyaml.start()
        self.myaml.load.side_effect = lambda fp: self.options
        self._pconfig = mock.patch.object(hookenv, 'config')
        self.mconfig = self._pconfig.start()
        self.mconfig.side_effect = lambda: self.config
        self._pcharm_dir = mock.patch.object(hookenv, 'charm_dir')
        self.mcharm_dir = self._pcharm_dir.start()
        self.mcharm_dir.return_value = 'charm_dir'

    def tearDown(self):
        self._pyaml.stop()
        self._pconfig.stop()
        self._pcharm_dir.stop()

    def test_none_changed(self):
        with mock.patch.object(services.helpers, 'open', mock.mock_open(), create=True):
            context = services.helpers.RequiredConfig('option1', 'option2')
        self.assertFalse(bool(context))
        self.assertEqual(context['config']['option1'], None)
        self.assertEqual(context['config']['option2'], 0)

    def test_partial(self):
        self.config['option1'] = 'value'
        with mock.patch.object(services.helpers, 'open', mock.mock_open(), create=True):
            context = services.helpers.RequiredConfig('option1', 'option2')
        self.assertFalse(bool(context))
        self.assertEqual(context['config']['option1'], 'value')
        self.assertEqual(context['config']['option2'], 0)

    def test_ready(self):
        self.config['option1'] = 'value'
        self.config['option2'] = 1
        with mock.patch.object(services.helpers, 'open', mock.mock_open(), create=True):
            context = services.helpers.RequiredConfig('option1', 'option2')
        self.assertTrue(bool(context))
        self.assertEqual(context['config']['option1'], 'value')
        self.assertEqual(context['config']['option2'], 1)

    def test_none_empty(self):
        self.config['option1'] = ''
        self.config['option2'] = 1
        with mock.patch.object(services.helpers, 'open', mock.mock_open(), create=True):
            context = services.helpers.RequiredConfig('option1', 'option2')
        self.assertFalse(bool(context))
        self.assertEqual(context['config']['option1'], '')
        self.assertEqual(context['config']['option2'], 1)


class TestStoredContext(unittest.TestCase):
    @mock.patch.object(services.helpers.StoredContext, 'read_context')
    @mock.patch.object(services.helpers.StoredContext, 'store_context')
    @mock.patch('os.path.exists')
    def test_new(self, exists, store_context, read_context):
        exists.return_value = False
        context = services.helpers.StoredContext('foo.yaml', {'key': 'val'})
        assert not read_context.called
        store_context.assert_called_once_with('foo.yaml', {'key': 'val'})
        self.assertEqual(context, {'key': 'val'})

    @mock.patch.object(services.helpers.StoredContext, 'read_context')
    @mock.patch.object(services.helpers.StoredContext, 'store_context')
    @mock.patch('os.path.exists')
    def test_existing(self, exists, store_context, read_context):
        exists.return_value = True
        read_context.return_value = {'key': 'other'}
        context = services.helpers.StoredContext('foo.yaml', {'key': 'val'})
        read_context.assert_called_once_with('foo.yaml')
        assert not store_context.called
        self.assertEqual(context, {'key': 'other'})

    @mock.patch.object(hookenv, 'charm_dir', lambda: 'charm_dir')
    @mock.patch.object(services.helpers.StoredContext, 'read_context')
    @mock.patch.object(services.helpers, 'yaml')
    @mock.patch('os.fchmod')
    @mock.patch('os.path.exists')
    def test_store_context(self, exists, fchmod, yaml, read_context):
        exists.return_value = False
        mopen = mock.mock_open()
        with mock.patch.object(services.helpers, 'open', mopen, create=True):
            services.helpers.StoredContext('foo.yaml', {'key': 'val'})
        mopen.assert_called_once_with('charm_dir/foo.yaml', 'w')
        fchmod.assert_called_once_with(mopen.return_value.fileno(), 0o600)
        yaml.dump.assert_called_once_with({'key': 'val'}, mopen.return_value)

    @mock.patch.object(hookenv, 'charm_dir', lambda: 'charm_dir')
    @mock.patch.object(services.helpers.StoredContext, 'read_context')
    @mock.patch.object(services.helpers, 'yaml')
    @mock.patch('os.fchmod')
    @mock.patch('os.path.exists')
    def test_store_context_abs(self, exists, fchmod, yaml, read_context):
        exists.return_value = False
        mopen = mock.mock_open()
        with mock.patch.object(services.helpers, 'open', mopen, create=True):
            services.helpers.StoredContext('/foo.yaml', {'key': 'val'})
        mopen.assert_called_once_with('/foo.yaml', 'w')

    @mock.patch.object(hookenv, 'charm_dir', lambda: 'charm_dir')
    @mock.patch.object(services.helpers, 'yaml')
    @mock.patch('os.path.exists')
    def test_read_context(self, exists, yaml):
        exists.return_value = True
        yaml.load.return_value = {'key': 'other'}
        mopen = mock.mock_open()
        with mock.patch.object(services.helpers, 'open', mopen, create=True):
            context = services.helpers.StoredContext('foo.yaml', {'key': 'val'})
        mopen.assert_called_once_with('charm_dir/foo.yaml', 'r')
        yaml.load.assert_called_once_with(mopen.return_value)
        self.assertEqual(context, {'key': 'other'})

    @mock.patch.object(hookenv, 'charm_dir', lambda: 'charm_dir')
    @mock.patch.object(services.helpers, 'yaml')
    @mock.patch('os.path.exists')
    def test_read_context_abs(self, exists, yaml):
        exists.return_value = True
        yaml.load.return_value = {'key': 'other'}
        mopen = mock.mock_open()
        with mock.patch.object(services.helpers, 'open', mopen, create=True):
            context = services.helpers.StoredContext('/foo.yaml', {'key': 'val'})
        mopen.assert_called_once_with('/foo.yaml', 'r')
        yaml.load.assert_called_once_with(mopen.return_value)
        self.assertEqual(context, {'key': 'other'})

    @mock.patch.object(hookenv, 'charm_dir', lambda: 'charm_dir')
    @mock.patch.object(services.helpers, 'yaml')
    @mock.patch('os.path.exists')
    def test_read_context_empty(self, exists, yaml):
        exists.return_value = True
        yaml.load.return_value = None
        mopen = mock.mock_open()
        with mock.patch.object(services.helpers, 'open', mopen, create=True):
            self.assertRaises(OSError, services.helpers.StoredContext, '/foo.yaml', {})


class TestTemplateCallback(unittest.TestCase):
    @mock.patch.object(services.helpers, 'templating')
    def test_template_defaults(self, mtemplating):
        manager = mock.Mock(**{'get_service.return_value': {
            'required_data': [{'foo': 'bar'}]}})
        self.assertRaises(TypeError, services.template, source='foo.yml')
        callback = services.template(source='foo.yml', target='bar.yml')
        assert isinstance(callback, services.ManagerCallback)
        assert not mtemplating.render.called
        callback(manager, 'test', 'event')
        mtemplating.render.assert_called_once_with(
            'foo.yml', 'bar.yml', {'foo': 'bar', 'ctx': {'foo': 'bar'}},
            'root', 'root', 0o444, template_loader=None)

    @mock.patch.object(services.helpers, 'templating')
    def test_template_explicit(self, mtemplating):
        manager = mock.Mock(**{'get_service.return_value': {
            'required_data': [{'foo': 'bar'}]}})
        callback = services.template(
            source='foo.yml', target='bar.yml',
            owner='user', group='group', perms=0o555
        )
        assert isinstance(callback, services.ManagerCallback)
        assert not mtemplating.render.called
        callback(manager, 'test', 'event')
        mtemplating.render.assert_called_once_with(
            'foo.yml', 'bar.yml', {'foo': 'bar', 'ctx': {'foo': 'bar'}},
            'user', 'group', 0o555, template_loader=None)

    @mock.patch.object(services.helpers, 'templating')
    def test_template_loader(self, mtemplating):
        manager = mock.Mock(**{'get_service.return_value': {
            'required_data': [{'foo': 'bar'}]}})
        callback = services.template(
            source='foo.yml', target='bar.yml',
            owner='user', group='group', perms=0o555,
            template_loader='myloader'
        )
        assert isinstance(callback, services.ManagerCallback)
        assert not mtemplating.render.called
        callback(manager, 'test', 'event')
        mtemplating.render.assert_called_once_with(
            'foo.yml', 'bar.yml', {'foo': 'bar', 'ctx': {'foo': 'bar'}},
            'user', 'group', 0o555, template_loader='myloader')

    @mock.patch.object(os.path, 'isfile')
    @mock.patch.object(host, 'file_hash')
    @mock.patch.object(host, 'service_restart')
    @mock.patch.object(services.helpers, 'templating')
    def test_template_onchange_restart(self, mtemplating, mrestart, mfile_hash, misfile):
        def random_string(arg):
            return uuid.uuid4()
        mfile_hash.side_effect = random_string
        misfile.return_value = True
        manager = mock.Mock(**{'get_service.return_value': {
            'required_data': [{'foo': 'bar'}]}})
        callback = services.template(
            source='foo.yml', target='bar.yml',
            owner='user', group='group', perms=0o555,
            on_change_action=(partial(mrestart, "mysuperservice")),
        )
        assert isinstance(callback, services.ManagerCallback)
        assert not mtemplating.render.called
        callback(manager, 'test', 'event')
        mtemplating.render.assert_called_once_with(
            'foo.yml', 'bar.yml', {'foo': 'bar', 'ctx': {'foo': 'bar'}},
            'user', 'group', 0o555, template_loader=None)
        mrestart.assert_called_with('mysuperservice')

    @mock.patch.object(hookenv, 'log')
    @mock.patch.object(os.path, 'isfile')
    @mock.patch.object(host, 'file_hash')
    @mock.patch.object(host, 'service_restart')
    @mock.patch.object(services.helpers, 'templating')
    def test_template_onchange_restart_nochange(self, mtemplating, mrestart,
                                                mfile_hash, misfile, mlog):
        mfile_hash.return_value = "myhash"
        misfile.return_value = True
        manager = mock.Mock(**{'get_service.return_value': {
            'required_data': [{'foo': 'bar'}]}})
        callback = services.template(
            source='foo.yml', target='bar.yml',
            owner='user', group='group', perms=0o555,
            on_change_action=(partial(mrestart, "mysuperservice")),
        )
        assert isinstance(callback, services.ManagerCallback)
        assert not mtemplating.render.called
        callback(manager, 'test', 'event')
        mtemplating.render.assert_called_once_with(
            'foo.yml', 'bar.yml', {'foo': 'bar', 'ctx': {'foo': 'bar'}},
            'user', 'group', 0o555, template_loader=None)
        self.assertEqual(mrestart.call_args_list, [])


class TestPortsCallback(unittest.TestCase):
    def setUp(self):
        self.phookenv = mock.patch.object(services.base, 'hookenv')
        self.mhookenv = self.phookenv.start()
        self.mhookenv.relation_ids.return_value = []
        self.mhookenv.charm_dir.return_value = 'charm_dir'
        self.popen = mock.patch.object(services.base, 'open', create=True)
        self.mopen = self.popen.start()

    def tearDown(self):
        self.phookenv.stop()
        self.popen.stop()

    def test_no_ports(self):
        manager = mock.Mock(**{'get_service.return_value': {}})
        services.PortManagerCallback()(manager, 'service', 'event')
        assert not self.mhookenv.open_port.called
        assert not self.mhookenv.close_port.called

    def test_open_ports(self):
        manager = mock.Mock(**{'get_service.return_value': {'ports': [1, 2]}})
        services.open_ports(manager, 'service', 'start')
        self.mhookenv.open_port.has_calls([mock.call(1), mock.call(2)])
        assert not self.mhookenv.close_port.called

    def test_close_ports(self):
        manager = mock.Mock(**{'get_service.return_value': {'ports': [1, 2]}})
        services.close_ports(manager, 'service', 'stop')
        assert not self.mhookenv.open_port.called
        self.mhookenv.close_port.has_calls([mock.call(1), mock.call(2)])

    def test_close_old_ports(self):
        self.mopen.return_value.read.return_value = '10,20'
        manager = mock.Mock(**{'get_service.return_value': {'ports': [1, 2]}})
        services.close_ports(manager, 'service', 'stop')
        assert not self.mhookenv.open_port.called
        self.mhookenv.close_port.has_calls([
            mock.call(10),
            mock.call(20),
            mock.call(1),
            mock.call(2)])


if __name__ == '__main__':
    unittest.main()
