# Copyright 2021 Canonical Limited.
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

# Functions for managing deferred events.

import collections
import datetime
import time

import charmhelpers.core as ch_core
import charmhelpers.contrib.openstack.policy_rcd as policy_rcd
import charmhelpers.core.hookenv as hookenv
import charmhelpers.core.host as host

import subprocess


ServiceEvent = collections.namedtuple(
    'ServiceEvent',
    'timestamp service reason action')


class DeferredServiceEvents():
    """A class to manage defered servce events."""

    def __init__(self):
        """Intialise deferred events class."""
        self.events = self.load_events()


class DeferredCharmServiceEvents(DeferredServiceEvents):
    """Deferred events from charm actions."""

    KV_KEY = 'deferred_events'

    def load_events(self):
        """Load events previously requested by the charm.

        :returns: List of events requested by the charm.
        :rtype: List[ServiceEvent]
        """
        with ch_core.unitdata.HookData()() as t:
            kv = t[0]
            queued_restarts = kv.get(self.KV_KEY, [])
        return [
            ServiceEvent(
                e['timestamp'], e['service'], e['reason'], e['action'])
            for e in queued_restarts]

    def add_event(self, service, action, event_reason=None):
        """Record that a service event was requested but deferred.

        :param services: Service which was to be restarted.
        :type services: str
        :param action: Action that was deferred
        :type action: str
        :param event_reason: Reason for needing to run the action.
        :type event_reason: str
        """
        if not event_reason:
            event_reason = 'Unknown'
        timestamp = round(time.time())
        self.events.append(ServiceEvent(
            timestamp=timestamp,
            service=service,
            reason=event_reason,
            action=action))
        self.save_events()

    def clear_deferred_events(self, services, action):
        """Clear deferred events.

        :param services: Services with deferred actions to clear.
        :type services: List[str]
        :param action: Action that was deferred
        :type action: str
        """
        filtered_restarts = [
            e
            for e in self.events
            if not (e.service in services and e.action == action)]
        self.events = filtered_restarts
        self.save_events()

    def save_events(self):
        """Write deferred events to backend."""
        # Use dict() to ensure the result is a dict not an OrderedDict which
        # is returned on 3.1 <= python < 3.8
        raw_events = [dict(e._asdict()) for e in self.events]
        with ch_core.unitdata.HookData()() as t:
            kv = t[0]
            kv.set(self.KV_KEY, raw_events)


class DeferredPackageServiceEvents(DeferredServiceEvents):
    """Deferred events from package actions."""

    def load_events(self):
        """Load events previously requested by the charm.

        :returns: List of events requested by the charm.
        :rtype: List[ServiceEvent]
        """
        queued_restarts = []
        for event in policy_rcd.policy_deferred_events():
            queued_restarts.append(
                ServiceEvent(
                    event['time'],
                    event['service'],
                    'Pkg Update',
                    event['action']))
        return queued_restarts

    def clear_deferred_events(self, services, action):
        """Clear deferred events.

        :param services: Services with deferred actions to clear.
        :type services: List[str]
        :param action: Action that was deferred
        :type action: str
        """
        policy_rcd.clear_deferred_pkg_events(services, action)


def get_deferred_events():
    """Return a list of deferred events requested by the charm and packages.

    :returns: List of deferred events
    :rtype: List[ServiceEvent]
    """
    return DeferredCharmServiceEvents().events + DeferredPackageServiceEvents().events


def get_deferred_restarts():
    """List of deferred restart events requested by the charm and packages.

    :returns: List of deferred restarts
    :rtype: List[ServiceEvent]
    """
    return [e for e in get_deferred_events() if e.action == 'restart']


def clear_deferred_events(services, action):
    """Clear deferred events of type `action` targetted at `services`.

    :param services: Services with deferred actions to clear.
    :type services: List[str]
    :param action: Action to clear
    :type action: str
    """
    DeferredCharmServiceEvents().clear_deferred_events(services, action)
    DeferredPackageServiceEvents().clear_deferred_events(services, action)


def clear_deferred_restarts(services):
    """Clear deferred restart events targetted at `services`.

    :param services: Services with deferred actions to clear.
    :type services: List[str]
    """
    clear_deferred_events(services, 'restart')


def process_svc_restart(service):
    """Respond to a service restart having occured.

    :param service: Services that the action was performed against.
    :type service: str
    """
    clear_deferred_restarts([service])


def is_restart_permitted():
    """Check whether restarts are permitted.

    :returns: Whether restarts are permitted
    :rtype: bool
    """
    if hookenv.config('enable-auto-restarts') is None:
        return True
    return hookenv.config('enable-auto-restarts')


def defer_restart_on_changed(service, changed_files):
    """Check if restarts are permitted, if they are not defer them.

    :param service: Service to be restarted
    :type service: str
    :param changed_files: Files that have changed to trigger restarts.
    :type changed_files: List[str]
    :returns: Whether restarts are permitted
    :rtype: bool
    """
    permitted = is_restart_permitted()
    if not permitted:
        charm_events = DeferredCharmServiceEvents()
        charm_events.add_event(
            service,
            event_reason='File(s) changed: {}'.format(
                ', '.join(changed_files)),
            action='restart')
    return permitted


def deferrable_svc_restart(svc, reason=None):
    """Restarts service if permitted, if not defer it.

    :returns: Whether restarts are permitted
    :rtype: bool
    """
    if is_restart_permitted():
        host.service_restart(svc)
    else:
        charm_events = DeferredCharmServiceEvents()
        charm_events.add_event(
            svc,
            event_reason=reason,
            action='restart')


def configure_deferred_restarts(services):
    """Setup deferred restarts.

    :param services: Services to block restarts of.
    :type services: List[str]
    """
    policy_rcd.install_policy_rcd()
    if is_restart_permitted():
        policy_rcd.remove_policy_file()
    else:
        blocked_actions = ['stop', 'restart', 'try-restart']
        for svc in services:
            policy_rcd.add_policy_block(svc, blocked_actions)


def get_service_start_time(service):
    """Find point in time when the systemd unit transitioned to active state.

    :param service: Services to check timetsamp of.
    :type service: str
    """
    start_time = None
    out = subprocess.check_output(
        [
            'systemctl',
            'show',
            service,
            '--property=ActiveEnterTimestamp'])
    str_time = out.decode().rstrip().replace('ActiveEnterTimestamp=', '')
    if str_time:
        start_time = datetime.datetime.strptime(
            str_time,
            '%a %Y-%m-%d %H:%M:%S %Z')
    return start_time


def check_restarts():
    """Check deferred restarts against systemd units start time.

    Check if a service has a deferred event and clear it if it has been
    subsequently restarted.
    """
    for event in get_deferred_restarts():
        start_time = get_service_start_time(event.service)
        deferred_restart_time = datetime.datetime.fromtimestamp(
            event.timestamp)
        if start_time and start_time < deferred_restart_time:
            hookenv.log(
                ("Restart still required, {} was started at {}, restart was "
                 "requested after that at {}").format(
                    event.service,
                    start_time,
                    deferred_restart_time),
                level='DEBUG')
        else:
            clear_deferred_restarts([event.service])
