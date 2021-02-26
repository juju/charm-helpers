import contextlib
import datetime
from copy import deepcopy

from mock import MagicMock, patch, call

import charmhelpers.contrib.openstack.deferred_events as deferred_events
import tests.utils


class DeferredCharmServiceEventsTestCase(tests.utils.BaseTestCase):

    def setUp(self):
        super(DeferredCharmServiceEventsTestCase, self).setUp()
        self.patch_object(deferred_events.ch_core.unitdata, 'HookData')
        self.kv = MagicMock()

        self.event_a = {
            'timestamp': 123,
            'service': 'svcA',
            'reason': 'ReasonA',
            'action': 'restart'}
        self.event_b = {
            'timestamp': 223,
            'service': 'svcB',
            'reason': 'ReasonB',
            'action': 'restart'}
        self.kv_data = [self.event_a, self.event_b]
        self.kv.get.return_value = self.kv_data

        @contextlib.contextmanager
        def hook_data__call__():
            yield (self.kv, True, False)

        hook_data__call__.return_value = (self.kv, True, False)
        self.HookData.return_value = hook_data__call__
        self.test_class = deferred_events.DeferredCharmServiceEvents()
        self.exp_event_a = deferred_events.ServiceEvent(
            timestamp=123,
            service='svcA',
            reason='ReasonA',
            action='restart')
        self.exp_event_b = deferred_events.ServiceEvent(
            timestamp=223,
            service='svcB',
            reason='ReasonB',
            action='restart')
        self.base_expect_events = [self.exp_event_a, self.exp_event_b]

    def test_load_events(self):
        self.assertEqual(
            self.test_class.load_events(),
            self.base_expect_events)

    def test_add_event(self):
        self.patch_object(deferred_events.time, 'time')
        self.time.return_value = 456
        self.test_class.add_event('ovs-agent', 'restart', 'A Reason')
        _expect = deepcopy(self.base_expect_events)
        _expect.append(deferred_events.ServiceEvent(
            timestamp=456,
            service='ovs-agent',
            reason='A Reason',
            action='restart'))
        self.assertEqual(
            self.test_class.events,
            _expect)

    def test_clear_deferred_events(self):
        self.test_class.clear_deferred_events(['svcA'], 'restart')
        self.assertEqual(
            self.test_class.events,
            [self.exp_event_b])

    def test_clear_deferred_events_all(self):
        self.test_class.clear_deferred_events(['svcA', 'svcB'], 'restart')
        self.assertEqual(
            self.test_class.events,
            [])

    def test_clear_deferred_events_action_miss(self):
        self.test_class.clear_deferred_events(['svcA', 'svcB'], 'stop')
        self.assertEqual(
            self.test_class.events,
            self.base_expect_events)

    def test_save_events(self):
        self.test_class.save_events()
        self.kv.set.assert_called_once_with('deferred_events', self.kv_data)

    @patch.object(deferred_events.policy_rcd, 'policy_deferred_events')
    def test_load(self, policy_deferred_events):
        policy_deferred_events.return_value = [
            {
                'time': 123,
                'service': 'svcA',
                'action': 'restart'},
            {
                'time': 223,
                'service': 'svcB',
                'action': 'restart'}]
        self.assertEqual(
            deferred_events.DeferredPackageServiceEvents().events,
            [
                deferred_events.ServiceEvent(
                    timestamp=123,
                    service='svcA',
                    reason='Pkg Update',
                    action='restart'),
                deferred_events.ServiceEvent(
                    timestamp=223,
                    service='svcB',
                    reason='Pkg Update',
                    action='restart')])

    @patch.object(deferred_events.policy_rcd, 'policy_deferred_events')
    @patch.object(deferred_events.policy_rcd, 'clear_deferred_pkg_events')
    def test_clear_deferred_events_pkg(self, clear_deferred_pkg_events, policy_deferred_events):
        policy_deferred_events.return_value = []
        test_class = deferred_events.DeferredPackageServiceEvents()
        test_class.clear_deferred_events(['svcA', 'svcB'], 'restart')
        clear_deferred_pkg_events.assert_called_once_with(
            ['svcA', 'svcB'],
            'restart')

    @patch.object(deferred_events.policy_rcd, 'policy_deferred_events')
    def test_get_deferred_events(self, policy_deferred_events):
        policy_deferred_events.return_value = [
            {
                'time': 123,
                'service': 'svcA',
                'action': 'restart'},
            {
                'time': 223,
                'service': 'svcB',
                'action': 'restart'}]

        self.assertEqual(
            deferred_events.get_deferred_events(),
            [
                deferred_events.ServiceEvent(
                    timestamp=123,
                    service='svcA',
                    reason='ReasonA',
                    action='restart'),
                deferred_events.ServiceEvent(
                    timestamp=223,
                    service='svcB',
                    reason='ReasonB',
                    action='restart'),
                deferred_events.ServiceEvent(
                    timestamp=123,
                    service='svcA',
                    reason='Pkg Update',
                    action='restart'),
                deferred_events.ServiceEvent(
                    timestamp=223,
                    service='svcB',
                    reason='Pkg Update',
                    action='restart')])

    @patch.object(deferred_events, 'get_deferred_events')
    def test_get_deferred_restarts(self, get_deferred_events):
        get_deferred_events.return_value = [
            deferred_events.ServiceEvent(
                timestamp=123,
                service='svcA',
                reason='ReasonA',
                action='restart'),
            deferred_events.ServiceEvent(
                timestamp=223,
                service='svcB',
                reason='ReasonB',
                action='stop'),
            deferred_events.ServiceEvent(
                timestamp=123,
                service='svcA',
                reason='Pkg Update',
                action='start')]
        self.assertEqual(
            deferred_events.get_deferred_restarts(),
            [
                deferred_events.ServiceEvent(
                    timestamp=123,
                    service='svcA',
                    reason='ReasonA',
                    action='restart')])

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

    @patch.object(deferred_events, 'config')
    def is_restart_permitted(self, config):
        config.return_value = None
        self.assertTrue(deferred_events.is_restart_permitted())
        config.return_value = True
        self.assertTrue(deferred_events.is_restart_permitted())
        config.return_value = False
        self.assertFalse(deferred_events.is_restart_permitted())

    @patch.object(deferred_events, 'DeferredCharmServiceEvents')
    @patch.object(deferred_events, 'is_restart_permitted')
    def test_defer_restart_on_changed(self, is_restart_permitted,
                                      DeferredCharmServiceEvents):
        is_restart_permitted.return_value = False
        deferred_events.defer_restart_on_changed(
            ['svcA', 'svcB'],
            ['/tmp/test1.conf', '/tmp/test2.conf'])
        DeferredCharmServiceEvents().add_event(
            'svcA',
            action='restart',
            event_reason='File(s) changed: /tmp/test1.conf, /tmp/test2.conf')

    @patch.object(deferred_events, 'DeferredCharmServiceEvents')
    @patch.object(deferred_events.host, 'service_restart')
    @patch.object(deferred_events, 'is_restart_permitted')
    def test_deferrable_svc_restart(self, is_restart_permitted,
                                    service_restart, DeferredCharmServiceEvents):
        is_restart_permitted.return_value = True
        deferred_events.deferrable_svc_restart('svcA', reason='ReasonA')
        service_restart.assert_called_once_with('svcA')
        service_restart.reset_mock()
        is_restart_permitted.return_value = False
        deferred_events.deferrable_svc_restart('svcA', reason='ReasonA')
        self.assertFalse(service_restart.called)
        DeferredCharmServiceEvents().add_event(
            'svcA', action='restart', event_reason='ReasonA')

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
    def test_check_restarts(self, get_service_start_time, log,
                            clear_deferred_restarts, get_deferred_restarts):
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
        deferred_events.check_restarts()
        clear_deferred_restarts.assert_called_once_with(['svcA'])

        clear_deferred_restarts.reset_mock()
        get_service_start_time.return_value = datetime.datetime.strptime(
            'Tue 2021-02-02 10:10:55 UTC',
            '%a %Y-%m-%d %H:%M:%S %Z')
        deferred_events.check_restarts()
        self.assertFalse(clear_deferred_restarts.called)
        log.assert_called_once_with(
            ('Restart still required, svcA was started at 2021-02-02 10:10:55,'
             ' restart was requested after that at 2021-02-02 10:19:55'),
            level='DEBUG')
