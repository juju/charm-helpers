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
coordinate operations between units of a service.

:author: Stuart Bishop <stuart.bishop@canonical.com>


Services Framework Usage
========================

Ensure a peer relation is defined in metadata.yaml. Instantiate a
BaseCoordinator before invoking ServiceManager.manage().

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
                     data_ready=[maybe_restart])]

    if __name__ == '__main__':
        manager = services.ServiceManager(services)
        manager.manage()



Traditional Usage
=================

Ensure a peer relationis defined in metadata.yaml.

If you are using charmhelpers.core.hookenv.Hooks, ensure that a
BaseCoordinator is instantiated before calling Hooks.execute.

If you are not using charmhelpers.core.hookenv.Hooks, ensure
that a BaseCoordinator is instantiated and its handle() method
invoked at the start of your leader-elected, leader-settings-changed
and peer relation-changed hooks.

For example::

    from charmhelpers.core import hookenv

    hooks = hookenv.Hooks()

    def maybe_restart():
        serial = coordinator.Serial()
        if serial.granted('restart'):
            hookenv.service_restart('myservice')

    @hooks.hook
    def config_changed():
        update_config()
        serial = coordinator.Serial()
        # Lazy evaluation means the restart permission request
        # will only be made if necessary, avoiding hook storms.
        if needs_restart() and serial.aquire('restart'):
            maybe_restart()

    @hooks.hook
    def cluster_relation_changed():
        serial = coordinator.Serial()
        serial.handle() # MUST ALWAYS be called from peer relation-changed
        maybe_restart()

    @hooks.hook
    def leader_settings_changed():
        serial = coordinator.Serial()
        serial.handle() # MUST ALWAYS be called from leader_settings_changed
        maybe_restart()

    if __name__ == '__main__':
        hooks.execute()


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
after the source hook as completed and the lock will never be granted
immediately, so the only opportunity the unit has has to perform the
action is in the leader-settings-changed hook. If the unit is the leader
and cannot grant its own lock, then the only opportunity for it to
perform the action is when a peer releases a lock, which triggers the
peer relation-changed on all units including the leader. This would be
simpler if leader-settings-changed was invoked on the leader, but that
not the case with Juju 1.23 leadership. I chose not to implement a
callback model, where a callback was passed to aquire() to be executed
as soon as the lock is granted, because the callback may become invalid
between making the request and being granted the lock due to a
'juju upgrade-charm' being run in the interim.
'''
from datetime import datetime
import json
import os.path

from charmhelpers.core import hookenv


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args,
                                                                 **kwargs)
        return cls._instances[cls]


class BaseCoordinator(object):
    # We make this a singleton so that if we need to spill to local
    # storage then only a single instance does so, rather than having
    # multiple instances stomp over each other.
    __metaclass__ = Singleton

    relid = None  # Peer relation-id, set by __init__
    relname = None

    grants = None  # self.grants[unit][permission] == timestamp
    requests = None  # self.requests[unit][permission] == timestamp

    def __init__(self, relation_key='coordinator', peer_relation_name=None):
        '''Instatiate a Coordinator.

        Data is stored on the peer relation and in leadership storage
        under the provided relation_key.

        The peer relation is identified by peer_relation_name, and defaults
        to the first one found in metadata.yaml.
        '''
        # Most initialization is deferred, since invoking hook tools from
        # the constructor makes testing hard.
        self.key = relation_key
        self.relname = peer_relation_name

        # Ensure that handle() is called, without placing that burden on
        # the charm author. They still need to do this manually if they
        # are not using a hook framework. Handle also invokes all the
        # deferred initialization.
        hookenv.atstart(self.handle)

    def acquire(self, lock):
        '''Aquire the named lock, non-blocking.

        The lock may be granted immediately, or in a future hook.

        Returns True if the lock has been granted. The lock will be
        automatically released at the end of the hook in which it is
        granted.

        Do not mindlessly call this method, as it causes hooks to be
        triggered. It should almost always be guarded by some condition.
        For example, if you call aquire() every time in your peer
        relation-changed hook you will end up with an infinite loop of
        hooks.
        '''
        unit = hookenv.local_unit()
        ts = self.requests[unit].get(lock)
        if not ts:
            # If there is no outstanding request on the peer relation,
            # create one.
            self.requests.setdefault(lock, {})
            self.requests[unit][lock] = _timestamp()

        # If the leader has granted the lock, yay.
        if self.granted(lock):
            return True

        # If the unit making the request also happens to be the
        # leader, it must handle the request now. Even though the
        # request has been stored on the peer relation, that does
        # cause the the peer relation-changed hook to be triggered.
        if hookenv.is_leader():
            return self.grant(lock, unit)

    def granted(self, lock):
        '''Return True if a previously requested lock has been granted'''
        unit = hookenv.local_unit()
        ts = self.requests[unit].get(lock)
        if ts and self.grants.get(unit, {}).get(lock) == ts:
            return True
        return False

    def handle(self):
        self._initialize()

        if not hookenv.is_leader():
            return  # Only the leader can grant requests.

        # Clear our grants that have been released.
        for unit in self.grants.keys():
            for permission, grant_ts in self.grants[unit].items():
                req_ts = self.requests.get(unit, {}).get(permission)
                if req_ts != grant_ts:
                    # The request timestamp does not match the granted
                    # timestamp. Several hooks on 'unit' may have run
                    # before the leader got a chance to make a decision,
                    # and 'unit' may have released its lock and attempted
                    # to reaquire it. This will change the timestamp,
                    # and we correctly revoke the old grant putting it
                    # to the end of the queue.
                    del self.grants[unit][permission]

        # Grant permissions
        for unit in self.requests.keys():
            for lock in self.requests[unit]:
                self.grant(lock, unit)

    def grant(self, lock, unit):
        '''Maybe grant the lock to a unit.

        The decision to grant the lock or not is made for $lock
        by a corresponding method grant_$lock, which you may define
        in a subclass. If no such method is defined, the default_grant
        method is used. See Serial.default_grant() for details.
        '''
        if not hookenv.is_leader():
            return False  # Not the leader, so we cannot grant.

        # Set of units already granted the lock.
        granted = set()
        for u in self.grants:
            for l in self.grants[u]:
                if l == lock:
                    if u == unit:
                        return True  # Already granted.
                    granted.add(u)

        # Ordered list of units waiting for the lock.
        reqs = set()
        for u in self.requests:
            for l, ts in self.requests[u].items():
                if l == lock:
                    reqs.add((ts, u))
        queue = [t[1] for t in sorted(reqs)]
        if unit not in queue:
            return False  # Unit has not requested the lock.

        # Locate custom logic, or fallback to the default.
        grant_func = getattr(self, 'grant_{}'.format(lock), self.default_grant)

        if grant_func(unit, granted, queue):
            # Grant the lock.
            self.grants.setdefault(unit, {})[lock] = self.requests[unit][lock]
            return True

        return False

    def _initialize(self):
        if self.requests is not None:
            return  # Already initialized.

        if self.relname is None:
            self.relname = _implicit_peer_relation_name()

        relids = hookenv.relation_ids(self.relname)
        if relids:
            self.relid = sorted(relids)[0]

        # Load our state, from leadership, the peer relationship, and maybe
        # local state as a fallback. Populates self.requests and self.grants.
        self._load_state()

        # Save our state if the hook completes successfully.
        hookenv.atexit(self._save_state)

        # Schedule release of granted locks for the end of the hook.
        # This needs to be the last of our atexit callbacks to ensure
        # it will be run first when the hook is complete, because there
        # is no point mutating our state after it has been saved.
        hookenv.atexit(self._release_granted)

    def _load_state(self):
        # All responses must be stored in the leadership settings.
        # The leader cannot use local state, as a different unit may
        # be leader next time. Which is fine, as the leadership
        # settings are always available.
        self.grants = json.loads(hookenv.leader_get(self.key) or '{}')

        local_unit = hookenv.local_unit()

        # All requests must be stored on the peer relation. This is
        # the only channel units have to communicate with the leader.
        # Even the leader needs to store its requests here, as a
        # different unit may be leader by the time the request can be
        # granted.
        self.requests = {}
        if self.relid is None:
            # The peer relation is not available. Maybe we are early in
            # the leader's lifecycle. Maybe this unit is standalone.
            # Fallback to using local state.
            self.requests[local_unit] = self._load_local_state()
        else:
            units = set(hookenv.related_units(self.relid))
            units.add(local_unit)
            for unit in units:
                raw = hookenv.relation_get(self.key, unit, self.relid)
                if raw:
                    self.requests[unit] = json.loads(raw)
            if local_unit not in self.requests:
                # The peer relation has just been joined. Update any state
                # loaded from our peers with our local state.
                self.requests[local_unit] = self._load_local_state()

    def _save_state(self):
        if hookenv.is_leader():
            # sort_keys to ensure stability.
            raw = json.dumps(self.grants, sort_keys=True)
            hookenv.leader_set({self.key: raw})

        if self.relid is None:
            # No peer relation yet. Fallback to local state.
            self._save_local_state()
        else:
            local_unit = hookenv.local_unit()
            # sort_keys to ensure stability.
            raw = json.dumps(self.requests[local_unit], sort_keys=True)
            hookenv.relation_set(self.relid, relation_settings={self.key: raw})

    def _local_state_filename(self):
        # Include the class name. We allow multiple BaseCoordinator
        # subclasses to be instantiated, and they are singletons, so
        # this avoids conflicts (unless someone creates and uses two
        # BaseCoordinator subclasses with the same class name, so don't
        # do that).
        return '.charmhelpers.coordinator.{}'.format(self.__class__.__name__)

    def _load_local_state(self):
        fn = self._local_state_filename()
        if os.path.exists(fn):
            with open(fn, 'r') as f:
                return json.load(f)
        return {}

    def _save_local_state(self, state):
        fn = self._local_state_filename()
        with open(fn, 'w') as f:
            json.dump(state, f)

    def _release_granted(self):
        # At the end of every hook, release all locks granted to
        # this unit. If a hook neglects to make use of what it
        # requested, it will just have to make the request again.
        # Implicit release is the only way this will work, as
        # if the unit is standalone there may be no future triggers
        # called to do a manual release.
        unit = hookenv.local_unit()
        for lock in self.requests[unit].keys():
            if self.granted(lock):
                del self.requests[unit][lock]


class Serial(BaseCoordinator):
    def default_grant(self, unit, granted, queue):
        '''Default logic to grant a lock to a unit. Unless overridden,
        only one unit may hold the lock and it will be granted to the
        earliest queued request.

        To define custom logic for $lock, create a subclass and
        define a grant_$lock method.

        `unit` is the unit name making the request.

        `granted` is the set of units already granted the lock. It will
        never include `unit`. It may be empty.

        `queue` is the list of units waiting for the lock, ordered by time
        of request. It will always include `unit`, but `unit` is not
        necessarily first.

        Returns True if the lock should be granted to `unit`.
        '''
        return unit == queue[0] and not granted


def _implicit_peer_relation_name():
    md = hookenv.metadata()
    assert 'peers' in md, 'No peer relations in metadata.yaml'
    return sorted(md['peers'].keys())[0]


def _timestamp():
    '''A human readable yet sortable timestamp'''
    return datetime.utcnow().strftime('%Y-%m-%d %H:%M:%SZ')
