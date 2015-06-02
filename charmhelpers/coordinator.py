# Copyright 2014-2015 Canonical Limited.
#
# This file is part of charm-helpers.
#
# charm-helpers is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version 3 as
# published by the Free Software Foundation.
#
# charm-helpers is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with charm-helpers.  If not, see <http://www.gnu.org/licenses/>.

'''
The coordinator module allows you to use Juju's leadership feature to
coordinate actions between units of a service. It requires Juju 1.23 or
later.


Services Framework Usage
========================

Ensure a peer relation is defined in metadata.yaml. Ensure your
ServiceManager's manage method is always invoked in the leader-elected,
leader-settings-changed and peer relation-changed hooks.

Instantiate a BaseCoordinator (eg. coordinator.Serial). Add the
instance to your service's provided_data list.

For example::

    from charmhelpers.core import services
    from charmhelpers import coordinator

    serial = coordinator.Serial()

    def maybe_restart(servicename):
        # Lazy evaluation means the restart permission request
        # will only be made if necessary, avoiding hook storms.
        if needs_restart() and serial.aquire('restart'):
            hookenv.service_restart(servicename)

    services = [dict(service='servicename',
                     provided_data=[serial],
                     data_ready=[maybe_restart])]

    if __name__ == '__main__':
        manager = services.ServiceManager(services)
        manager.manage()



Traditional Usage
=================

Ensure a peer relationis defined in metadata.yaml. Ensure that a
BaseCoordinator is instatiated in the leader-elected,
leader-settings-changed and peer relation-changed hooks.

For example::

    def maybe_restart():
        serial = coordinator.Serial()
        if serial.granted('restart'):
            hookenv.service_restart('myservice')

    @hook
    def config_changed():
        update_config()
        serial = coordinator.Serial()
        # Lazy evaluation means the restart permission request
        # will only be made if necessary, avoiding hook storms.
        if needs_restart() and serial.aquire('restart'):
            maybe_restart()

    @hook
    def cluster_relation_changed():
        serial = coordinator.Serial()
        serial.handle() # MUST ALWAYS be called from peer relation-changed
        maybe_restart()

    @hook
    def leader_settings_changed():
        serial = coordinator.Serial()
        serial.handle() # MUST ALWAYS be called from leader_settings_changed
        maybe_restart()

    
API
===

A simple API is provided similar to traditional locking APIs. A
permission may be requested using the aquire() method, and the
granted() method may be used do to check if a permission previously
aquired has been granted. It doesn't matter how many times aquire()
is called in a hook.

Permissions are released at the end of the hook if the requests
could be aquired immediately. All granted permissions are released
by the leader-settings-changed hook.

Whenever a charm needs to perform a coordinated action it will aquire()
the permission and perform the action immediately if aquisition is
successful. It will also need to perform the same action in both the
leader-settings-changed hook and peer relation-changed hooks if the
permission has been granted.


Grubby Details
--------------

Why do you need to be able to perform the same action in three places?
If the unit is the leader, then it may be able to grant its own lock
and perform the action immediately in the source hook. If the unit is
not the leader, then the leader will not be aware of the request until
after the source hook as completed and the only opportunity it has to
perform the action is in the leader-settings-changed hook. If the unit
is the leader and cannot grant its own lock, then the only opportunity
for it to perform the action is when a peer releases a lock which
triggers the peer relation-changed on all units including the leader.
This would be simpler if leader-settings-changed was invoked on the
leader, but that not the case with Juju 1.23 leadership. I chose not to
implement a callback model, where a callback was passed to aquire() to
be executed as soon as the lock is granted, because the callback may
become invalid between making the request and being granted the lock
due to a juju upgrade-charm being run in the interim.
'''

from datetime import datetime
import json

from charmhelpers.core import hookenv


class BaseCoordinator:
    relid = None  # Peer relation-id
    local_status = None

    def __init__(self, relation_key='coordinator', peer_relation_name=None):
        '''Instatiate a Coordinator.

        Data is stored on the peer relation and in leadership storage
        under the provided relation_key.
        
        The peer relation is identified by peer_relation_name, and defaults
        to the first one found in metadata.yaml.
        '''
        self.key = relation_key

        if peer_relation_name is None:
            peer_relation_name = _implicit_peer_relation_name()

        relids = hookenv.relation_ids(peer_relation_name)
        if relids:
            self.relid = sorted(relids)[0]

        self._load_state()

    def _load_state(self):
        # All responses must be stored in the leadership settings.
        # The leader cannot use local state, as a different unit may
        # be leader next time.
        # self.grants[token][unit] == timestamp
        self.grants = json.loads(hookenv.leader_get(self.key) or '{}')

        # All requests must be stored on the peer relation. This is
        # the only channel units have to communicate with the leader.
        # Even the leader needs to store its requests here, as a
        # different unit may be leader by the time the request can be
        # granted. Note that we might not have joined the peer relation
        # yet, in which case we fallback to local persistent storage.
        self.requests = {}  # self.requests[token][unit] == timestamp
        if self.relid is None:
            raise NotImplementedError('Need to load from local state')
        else:
            units = set(hookenv.related_units(self.relid))
            units.add(hookenv.local_unit())
            for unit in units:
                unit_reqs = json.loads(hookenv.relation_get(self.key,
                                                            unit,
                                                            self.relid)
                                       or '[]')
                for token, timestamp in unit_reqs:
                    self.requests.setdefault(token, {})
                    self.requests[token][unit] = timestamp

    def _save_state(self):
        if self.relid is None:
            raise NotImplementedError('Need to store to local state')
        else:
            local_unit = hookenv.local_unit()
            local_requests = []
            for token, token_requests in self.requests.values():
                if local_unit in token_requests:
                    local_requests.append((token, token_requests[local_unit]))
            encoded = json.dumps(sorted(local_requests))
            hookenv.relation_set(self.relid,
                                 relation_settings={self.key: encoded})

        if hookenv.is_leader():
            hookenv.leader_set({self.key: json.dumps(self.grants,
                                                     sort_keys=True)})

    def acquire(self, lock):
        '''Aquire the named lock, non-blocking.

        In most cases, the lock will not be granted until a future hook.

        Returns True if the lock has been granted. If granted, it remains
        yours until explicitly released or the unit is destroyed.
        '''
        unit = hookenv.local_unit()
        existing = self.requests.get(lock, {}).get(unit)
        if not existing:
            # If there is no outstanding request on the peer relation,
            # create one.
            self.requests.setdefault(lock, {})
            self.requests[lock][unit] = _timestamp()
            self._save_state()

        # If the leader has granted the lock, yay.
        if unit in self.grants.get(lock, {}):
            return True

        # If the unit making the request also happens to be the
        # leader, it must handle the request now. Even though the
        # request has been stored on the peer relation, that does
        # cause the the peer relation-changed hook to be triggered.
        if hookenv.is_leader():
            return self.grant(lock, unit)

    def release(self, lock):
        existing = self.requests.get(lock, {}).get(unit)
        if existing:
            del self.requests[lock][unit]
            self._save_state()

        # If the leader just released a lock, we need to process any
        # pending requests or risk deadlock. We reprocess the entire
        # queue, as there might be interdependencies in the granting
        # logic (eg. don't allow a unit to reboot if there are any
        # cluster wide maintenance operations running).
        self.process()

    def process(self):
        if not hookenv.is_leader():
            return  # Only the leader can process requests.


def _implicit_peer_relation_name():
    md = hookenv.metadata()
    assert 'peers' in md, 'No peer relations in metadata.yaml'
    return sorted(md['peers'].keys())[0]


def _timestamp():
    '''A human readable yet sortable timestamp'''
    return datetime.utcnow().strftime('%Y-%m-%d %H:%M:%SZ')
