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
from datetime import datetime, timedelta
import unittest
from unittest.mock import call, patch

from charmhelpers import coordinator
from charmhelpers.core import hookenv


class TestCoordinator(unittest.TestCase):

    def setUp(self):
        del hookenv._atstart[:]
        del hookenv._atexit[:]
        hookenv.cache.clear()
        coordinator.Singleton._instances.clear()

        def install(patch):
            patch.start()
            self.addCleanup(patch.stop)

        install(patch.object(hookenv, 'local_unit', return_value='foo/1'))
        install(patch.object(hookenv, 'is_leader', return_value=False))
        install(patch.object(hookenv, 'metadata',
                             return_value={'peers': {'cluster': None}}))
        install(patch.object(hookenv, 'log'))

        # Ensure _timestamp always increases.
        install(patch.object(coordinator, '_timestamp',
                             side_effect=self._timestamp))

    def test_is_singleton(self):
        # BaseCoordinator and subclasses are singletons. Placing this
        # burden on charm authors is impractical, particularly if
        # libraries start wanting to use coordinator instances.
        # With singletons, we don't need to worry about sharing state
        # between instances or have them stomping on each other when they
        # need to serialize their state.
        self.assertTrue(coordinator.BaseCoordinator()
                        is coordinator.BaseCoordinator())
        self.assertTrue(coordinator.Serial() is coordinator.Serial())
        self.assertFalse(coordinator.BaseCoordinator() is coordinator.Serial())

    @patch('charmhelpers.core.hookenv.atstart')
    def test_implicit_initialize_and_handle(self, atstart):
        # When you construct a BaseCoordinator(), its initialize() and
        # handle() method are invoked automatically every hook. This
        # is done using hookenv.atstart
        c = coordinator.BaseCoordinator()
        atstart.assert_has_calls([call(c.initialize), call(c.handle)])

    @patch.object(hookenv, 'has_juju_version', return_value=False)
    def test_initialize_enforces_juju_version(self, has_juju_version):
        c = coordinator.BaseCoordinator()
        with self.assertRaises(AssertionError):
            c.initialize()
        has_juju_version.assert_called_once_with('1.23')

    @patch.object(hookenv, 'atexit')
    @patch.object(hookenv, 'has_juju_version', return_value=True)
    @patch.object(hookenv, 'relation_ids')
    def test_initialize(self, relation_ids, ver, atexit):
        # First initialization are done before there is a peer relation.
        relation_ids.return_value = []
        c = coordinator.BaseCoordinator()
        with patch.object(c, '_load_state') as _load_state:
            c.initialize()
            _load_state.assert_called_once_with()

        self.assertEqual(c.relname, 'cluster')
        self.assertIsNone(c.relid)
        relation_ids.assert_called_once_with('cluster')

        # Methods installed to save state and release locks if the
        # hook is successful.
        atexit.assert_has_calls([call(c._save_state),
                                 call(c._release_granted)])

        # If we have a peer relation, the id is stored.
        relation_ids.return_value = ['cluster:1']
        c = coordinator.BaseCoordinator()
        with patch.object(c, '_load_state'):
            c.initialize()
        self.assertEqual(c.relid, 'cluster:1')


    def test_acquire(self):
        c = coordinator.BaseCoordinator()
        lock = 'mylock'
        c.grants = {}
        c.requests = {hookenv.local_unit(): {}}

        # We are not the leader, so first acquire will return False.
        self.assertFalse(c.acquire(lock))

        # But the request is in the queue.
        self.assertTrue(c.requested(lock))
        ts = c.request_timestamp(lock)

        # A further attempts at acquiring the lock do nothing,
        # and the timestamp of the request remains unchanged.
        self.assertFalse(c.acquire(lock))
        self.assertEqual(ts, c.request_timestamp(lock))

        # Once the leader has granted the lock, acquire returns True.
        with patch.object(c, 'granted') as granted:
            granted.return_value = True
            self.assertTrue(c.acquire(lock))
            granted.assert_called_once_with(lock)

    def test_acquire_leader(self):
        # When acquire() is called by the leader, it needs
        # to make a grant decision immediately. It can't defer
        # making the decision until a future hook, as no future
        # hooks will be triggered.
        hookenv.is_leader.return_value = True
        c = coordinator.Serial()  # Not Base. Test hooks into default_grant.
        lock = 'mylock'
        unit = hookenv.local_unit()
        c.grants = {}
        c.requests = {unit: {}}
        with patch.object(c, 'default_grant') as default_grant:
            default_grant.side_effect = iter([False, True])

            self.assertFalse(c.acquire(lock))
            ts = c.request_timestamp(lock)

            self.assertTrue(c.acquire(lock))
            self.assertEqual(ts, c.request_timestamp(lock))

            # If it it granted, the leader doesn't make a decision again.
            self.assertTrue(c.acquire(lock))
            self.assertEqual(ts, c.request_timestamp(lock))

            self.assertEqual(default_grant.call_count, 2)

    def test_granted(self):
        c = coordinator.BaseCoordinator()
        unit = hookenv.local_unit()
        lock = 'mylock'
        ts = coordinator._timestamp()
        c.grants = {}

        # Unit makes a request, but it isn't granted
        c.requests = {unit: {lock: ts}}
        self.assertFalse(c.granted(lock))

        # Once the leader has granted the request, all good.
        # It does this by mirroring the request timestamp.
        c.grants = {unit: {lock: ts}}
        self.assertTrue(c.granted(lock))

        # The unit releases the lock by removing the request.
        c.requests = {unit: {}}
        self.assertFalse(c.granted(lock))

        # If the unit makes a new request before the leader
        # has had a chance to do its housekeeping, the timestamps
        # do not match and the lock not considered granted.
        ts = coordinator._timestamp()
        c.requests = {unit: {lock: ts}}
        self.assertFalse(c.granted(lock))

        # Until the leader gets around to its duties.
        c.grants = {unit: {lock: ts}}
        self.assertTrue(c.granted(lock))

    def test_requested(self):
        c = coordinator.BaseCoordinator()
        lock = 'mylock'
        c.requests = {hookenv.local_unit(): {}}
        c.grants = {}

        self.assertFalse(c.requested(lock))
        c.acquire(lock)
        self.assertTrue(c.requested(lock))

    def test_request_timestamp(self):
        # 
        c = coordinator.BaseCoordinator()
        lock = 'mylock'
        unit = hookenv.local_unit()

        c.requests = {unit: {}}
        c.grants = {}
        self.assertIsNone(c.request_timestamp(lock))

        now = datetime.utcnow()
        fmt = coordinator._timestamp_format
        c.requests = {hookenv.local_unit(): { lock: now.strftime(fmt)}}

        self.assertEqual(c.request_timestamp(lock), now)

    def test_implicit_peer_relation_name(self):
        self.assertEqual(coordinator._implicit_peer_relation_name(),
                         'cluster')

    _last_utcnow = datetime.utcnow()

    def _timestamp(self, ts=coordinator._timestamp):
        self._last_utcnow += timedelta(hours=1)
        return ts(lambda: self._last_utcnow)
