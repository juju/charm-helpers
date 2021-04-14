import contextlib
import copy
import datetime
import json
import tempfile
import shutil
import yaml

from mock import patch, call

import charmhelpers.contrib.openstack.deferred_events as deferred_events
import tests.utils


class TestDB(object):
    '''Test KV store for unitdata testing'''
    def __init__(self):
        self.data = {}
        self.flushed = False

    def get(self, key, default=None):
        result = self.data.get(key, default)
        if not result:
            return default
        return json.loads(result)

    def set(self, key, value):
        self.data[key] = json.dumps(value)
        return value

    def flush(self):
        self.flushed = True


class TestHookData(object):

    def __init__(self, kv):
        self.kv = kv

    @contextlib.contextmanager
    def __call__(self):
        yield self.kv, True, True


class DeferredCharmServiceEventsTestCase(tests.utils.BaseTestCase):

    def setUp(self):
        super(DeferredCharmServiceEventsTestCase, self).setUp()
        self.tmp_dir = tempfile.mkdtemp()
        self.addCleanup(lambda: shutil.rmtree(self.tmp_dir))
        self.patch_object(deferred_events.hookenv, 'service_name')
        self.service_name.return_value = 'myapp'
        self.patch_object(deferred_events.unitdata, 'HookData')
        self.db = TestDB()
        self.HookData.return_value = TestHookData(self.db)
        self.exp_event_a = deferred_events.ServiceEvent(
            timestamp=123,
            service='svcA',
            reason='ReasonA',
            action='restart',
            policy_requestor_name='myapp',
            policy_requestor_type='charm')
        self.exp_event_b = deferred_events.ServiceEvent(
            timestamp=223,
            service='svcB',
            reason='ReasonB',
            action='restart')
        self.exp_event_c = deferred_events.ServiceEvent(
            timestamp=323,
            service='svcB',
            reason='ReasonB',
            action='restart')
        self.base_expect_events = [
            self.exp_event_a,
            self.exp_event_b,
            self.exp_event_c]
        self.event_file_pair = []
        for index, event in enumerate(self.base_expect_events):
            event_file = '{}/{}.deferred'.format('/tmpdir', str(index))
            self.event_file_pair.append((
                event_file,
                event))

    def test_matching_request_event(self):
        self.assertTrue(
            self.exp_event_b.matching_request(
                self.exp_event_c))
        self.assertFalse(
            self.exp_event_a.matching_request(
                self.exp_event_b))

    @patch.object(deferred_events.glob, "glob")
    def test_deferred_events_files(self, glob):
        defer_files = [
            '/var/lib/policy-rc.d/charm-myapp/1612346300.deferred',
            '/var/lib/policy-rc.d/charm-myapp/1612346322.deferred',
            '/var/lib/policy-rc.d/charm-myapp/1612346360.deferred']

        glob.return_value = defer_files
        self.assertEqual(
            deferred_events.deferred_events_files(),
            defer_files)

    def test_read_event_file(self):
        with tempfile.NamedTemporaryFile('w') as ftmp:
            yaml.dump(vars(self.exp_event_a), ftmp)
            ftmp.flush()
            self.assertEqual(
                deferred_events.read_event_file(ftmp.name),
                self.exp_event_a)

    @patch.object(deferred_events, "deferred_events_files")
    def test_deferred_events(self, deferred_events_files):
        event_files = []
        expect = []
        for index, event in enumerate(self.base_expect_events):
            event_file = '{}/{}.deferred'.format(self.tmp_dir, str(index))
            with open(event_file, 'w') as f:
                yaml.dump(vars(event), f)
            event_files.append(event_file)
            expect.append((
                event_file,
                event))
        deferred_events_files.return_value = event_files
        self.assertEqual(
            deferred_events.deferred_events(),
            expect)

    @patch.object(deferred_events, "deferred_events")
    def test_duplicate_event_files(self, _deferred_events):
        _deferred_events.return_value = self.event_file_pair
        self.assertEqual(
            deferred_events.duplicate_event_files(self.exp_event_b),
            ['/tmpdir/1.deferred', '/tmpdir/2.deferred'])
        self.assertEqual(
            deferred_events.duplicate_event_files(deferred_events.ServiceEvent(
                timestamp=223,
                service='svcX',
                reason='ReasonX',
                action='restart')),
            [])

    @patch.object(deferred_events.uuid, "uuid1")
    def test_get_event_record_file(self, uuid1):
        uuid1.return_value = '89eb8258'
        self.assertEqual(
            deferred_events.get_event_record_file(
                'charm',
                'neutron-ovs'),
            '/var/lib/policy-rc.d/charm-neutron-ovs-89eb8258.deferred')

    @patch.object(deferred_events, "get_event_record_file")
    @patch.object(deferred_events, "duplicate_event_files")
    @patch.object(deferred_events, "init_policy_log_dir")
    def test_save_event(self, init_policy_log_dir, duplicate_event_files, get_event_record_file):
        duplicate_event_files.return_value = []
        test_file = '{}/test_save_event.yaml'.format(self.tmp_dir)
        get_event_record_file.return_value = test_file
        deferred_events.save_event(self.exp_event_a)
        with open(test_file, 'r') as f:
            contents = yaml.load(f)
        self.assertEqual(contents, vars(self.exp_event_a))

    @patch.object(deferred_events.os, "remove")
    @patch.object(deferred_events, "read_event_file")
    @patch.object(deferred_events, "deferred_events_files")
    def test_clear_deferred_events(self, deferred_events_files, read_event_file,
                                   remove):
        deferred_events_files.return_value = ['/tmp/file1']
        read_event_file.return_value = self.exp_event_a
        deferred_events.clear_deferred_events('svcB', 'restart')
        self.assertFalse(remove.called)
        deferred_events.clear_deferred_events('svcA', 'restart')
        remove.assert_called_once_with('/tmp/file1')

    @patch.object(deferred_events.os, "mkdir")
    @patch.object(deferred_events.os.path, "exists")
    def test_init_policy_log_dir(self, exists, mkdir):
        exists.return_value = True
        deferred_events.init_policy_log_dir()
        self.assertFalse(mkdir.called)
        exists.return_value = False
        deferred_events.init_policy_log_dir()
        mkdir.assert_called_once_with('/var/lib/policy-rc.d')

    @patch.object(deferred_events, "deferred_events")
    def test_get_deferred_events(self, _deferred_events):
        _deferred_events.return_value = self.event_file_pair
        self.assertEqual(
            deferred_events.get_deferred_events(),
            self.base_expect_events)

    @patch.object(deferred_events, "get_deferred_events")
    def test_get_deferred_restarts(self, get_deferred_events):
        test_events = copy.deepcopy(self.base_expect_events)
        test_events.append(
            deferred_events.ServiceEvent(
                timestamp=523,
                service='svcD',
                reason='StopReasonD',
                action='stop'))
        get_deferred_events.return_value = test_events
        self.assertEqual(
            deferred_events.get_deferred_restarts(),
            self.base_expect_events)

    @patch.object(deferred_events, 'clear_deferred_events')
    def test_clear_deferred_restarts(self, clear_deferred_events):
        deferred_events.clear_deferred_restarts(['svcA', 'svcB'])
        clear_deferred_events.assert_Called_once_with(
            ['svcA', 'svcB'],
            'restart')

    @patch.object(deferred_events, 'clear_deferred_restarts')
    def test_process_svc_restart(self, clear_deferred_restarts):
        deferred_events.process_svc_restart('svcA')
        clear_deferred_restarts.assert_called_once_with(
            ['svcA'])

    @patch.object(deferred_events.hookenv, 'config')
    def test_is_restart_permitted(self, config):
        config.return_value = None
        self.assertTrue(deferred_events.is_restart_permitted())
        config.return_value = True
        self.assertTrue(deferred_events.is_restart_permitted())
        config.return_value = False
        self.assertFalse(deferred_events.is_restart_permitted())

    @patch.object(deferred_events.time, 'time')
    @patch.object(deferred_events, 'save_event')
    @patch.object(deferred_events, 'is_restart_permitted')
    def test_check_and_record_restart_request(self, is_restart_permitted,
                                              save_event, time):
        time.return_value = 123
        is_restart_permitted.return_value = False
        deferred_events.check_and_record_restart_request(
            'svcA',
            ['/tmp/test1.conf', '/tmp/test2.conf'])
        save_event.assert_called_once_with(deferred_events.ServiceEvent(
            timestamp=123,
            service='svcA',
            reason='File(s) changed: /tmp/test1.conf, /tmp/test2.conf',
            action='restart'))

    @patch.object(deferred_events.time, 'time')
    @patch.object(deferred_events, 'save_event')
    @patch.object(deferred_events.host, 'service_restart')
    @patch.object(deferred_events, 'is_restart_permitted')
    def test_deferrable_svc_restart(self, is_restart_permitted,
                                    service_restart, save_event, time):
        time.return_value = 123
        is_restart_permitted.return_value = True
        deferred_events.deferrable_svc_restart('svcA', reason='ReasonA')
        service_restart.assert_called_once_with('svcA')
        service_restart.reset_mock()
        is_restart_permitted.return_value = False
        deferred_events.deferrable_svc_restart('svcA', reason='ReasonA')
        self.assertFalse(service_restart.called)
        save_event.assert_called_once_with(deferred_events.ServiceEvent(
            timestamp=123,
            service='svcA',
            reason='ReasonA',
            action='restart'))

    @patch.object(deferred_events.policy_rcd, 'add_policy_block')
    @patch.object(deferred_events.policy_rcd, 'remove_policy_file')
    @patch.object(deferred_events, 'is_restart_permitted')
    @patch.object(deferred_events.policy_rcd, 'install_policy_rcd')
    def test_configure_deferred_restarts(self, install_policy_rcd,
                                         is_restart_permitted,
                                         remove_policy_file, add_policy_block):
        is_restart_permitted.return_value = True
        deferred_events.configure_deferred_restarts(['svcA', 'svcB'])
        remove_policy_file.assert_called_once_with()
        install_policy_rcd.assert_called_once_with()

        remove_policy_file.reset_mock()
        install_policy_rcd.reset_mock()
        is_restart_permitted.return_value = False
        deferred_events.configure_deferred_restarts(['svcA', 'svcB'])
        self.assertFalse(remove_policy_file.called)
        install_policy_rcd.assert_called_once_with()
        add_policy_block.assert_has_calls([
            call('svcA', ['stop', 'restart', 'try-restart']),
            call('svcB', ['stop', 'restart', 'try-restart'])])

    @patch.object(deferred_events.subprocess, 'check_output')
    def test_get_service_start_time(self, check_output):
        check_output.return_value = (
            b'ActiveEnterTimestamp=Tue 2021-02-02 13:19:55 UTC')
        expect = datetime.datetime.strptime(
            'Tue 2021-02-02 13:19:55 UTC',
            '%a %Y-%m-%d %H:%M:%S %Z')
        self.assertEqual(
            deferred_events.get_service_start_time('svcA'),
            expect)
        check_output.assert_called_once_with(
            ['systemctl', 'show', 'svcA', '--property=ActiveEnterTimestamp'])

    @patch.object(deferred_events, 'get_deferred_restarts')
    @patch.object(deferred_events, 'clear_deferred_restarts')
    @patch.object(deferred_events.hookenv, 'log')
    @patch.object(deferred_events, 'get_service_start_time')
    def test_check_restart_timestamps(self, get_service_start_time, log,
                                      clear_deferred_restarts,
                                      get_deferred_restarts):
        deferred_restarts = [
            # 'Tue 2021-02-02 10:19:55 UTC'
            deferred_events.ServiceEvent(
                timestamp=1612261195.0,
                service='svcA',
                reason='ReasonA',
                action='restart')]
        get_deferred_restarts.return_value = deferred_restarts
        get_service_start_time.return_value = datetime.datetime.strptime(
            'Tue 2021-02-02 13:19:55 UTC',
            '%a %Y-%m-%d %H:%M:%S %Z')
        deferred_events.check_restart_timestamps()
        clear_deferred_restarts.assert_called_once_with(['svcA'])

        clear_deferred_restarts.reset_mock()
        get_service_start_time.return_value = datetime.datetime.strptime(
            'Tue 2021-02-02 10:10:55 UTC',
            '%a %Y-%m-%d %H:%M:%S %Z')
        deferred_events.check_restart_timestamps()
        self.assertFalse(clear_deferred_restarts.called)
        log.assert_called_once_with(
            ('Restart still required, svcA was started at 2021-02-02 10:10:55,'
             ' restart was requested after that at 2021-02-02 10:19:55'),
            level='DEBUG')

    def test_set_deferred_hook(self):
        deferred_events.set_deferred_hook('config-changed')
        self.assertEqual(self.db.get('deferred-hooks'), ['config-changed'])
        deferred_events.set_deferred_hook('leader-settings-changed')
        self.assertEqual(
            self.db.get('deferred-hooks'),
            ['config-changed', 'leader-settings-changed'])

    def test_get_deferred_hook(self):
        deferred_events.set_deferred_hook('config-changed')
        self.assertEqual(
            deferred_events.get_deferred_hooks(),
            ['config-changed'])

    def test_clear_deferred_hooks(self):
        deferred_events.set_deferred_hook('config-changed')
        deferred_events.set_deferred_hook('leader-settings-changed')
        self.assertEqual(
            deferred_events.get_deferred_hooks(),
            ['config-changed', 'leader-settings-changed'])
        deferred_events.clear_deferred_hooks()
        self.assertEqual(
            deferred_events.get_deferred_hooks(),
            [])

    def test_clear_deferred_hook(self):
        deferred_events.set_deferred_hook('config-changed')
        deferred_events.set_deferred_hook('leader-settings-changed')
        self.assertEqual(
            deferred_events.get_deferred_hooks(),
            ['config-changed', 'leader-settings-changed'])
        deferred_events.clear_deferred_hook('leader-settings-changed')
        self.assertEqual(
            deferred_events.get_deferred_hooks(),
            ['config-changed'])
