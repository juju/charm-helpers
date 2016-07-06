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
from datetime import datetime, timedelta
import json
import tempfile
import unittest
from mock import call, MagicMock, patch, sentinel

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
        install(patch.object(coordinator, '_utcnow',
                             side_effect=self._utcnow))

    _last_utcnow = datetime(2015, 1, 1, 00, 00)

    def _utcnow(self, ts=coordinator._timestamp):
        self._last_utcnow += timedelta(minutes=1)
        return self._last_utcnow

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

    @patch.object(hookenv, 'atstart')
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

        with patch.object(c, '_load_state') as _load_state, \
                patch.object(c, '_emit_state') as _emit_state:  # IGNORE: E127
            c.initialize()
            _load_state.assert_called_once_with()
            _emit_state.assert_called_once_with()

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
        with patch.object(c, '_load_state'), patch.object(c, '_emit_state'):
            c.initialize()
        self.assertEqual(c.relid, 'cluster:1')

        # If we are already initialized, nothing happens.
        c.grants = {}
        c.requests = {}
        c.initialize()

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
        c = coordinator.BaseCoordinator()
        lock = 'mylock'
        unit = hookenv.local_unit()

        c.requests = {unit: {}}
        c.grants = {}
        self.assertIsNone(c.request_timestamp(lock))

        now = datetime.utcnow()
        fmt = coordinator._timestamp_format
        c.requests = {hookenv.local_unit(): {lock: now.strftime(fmt)}}

        self.assertEqual(c.request_timestamp(lock), now)

    def test_handle_not_leader(self):
        c = coordinator.BaseCoordinator()
        # If we are not the leader, handle does nothing. We know this,
        # because without mocks or initialization it would otherwise crash.
        c.handle()

    def test_handle(self):
        hookenv.is_leader.return_value = True
        lock = 'mylock'
        c = coordinator.BaseCoordinator()
        c.relid = 'cluster:1'

        ts = coordinator._timestamp
        ts1, ts2, ts3 = ts(), ts(), ts()

        # Grant one of these requests.
        requests = {'foo/1': {lock: ts1},
                    'foo/2': {lock: ts2},
                    'foo/3': {lock: ts3}}
        c.requests = requests.copy()
        # Because the existing grant should be released.
        c.grants = {'foo/2': {lock: ts()}}  # No request, release.

        with patch.object(c, 'grant') as grant:
            c.handle()

            # The requests are unchanged. This is normally state on the
            # peer relation, and only the units themselves can change it.
            self.assertDictEqual(requests, c.requests)

            # The grant without a corresponding requests was released.
            self.assertDictEqual({'foo/2': {}}, c.grants)

            # A potential grant was made for each of the outstanding requests.
            grant.assert_has_calls([call(lock, 'foo/1'),
                                    call(lock, 'foo/2'),
                                    call(lock, 'foo/3')], any_order=True)

    def test_grant_not_leader(self):
        c = coordinator.BaseCoordinator()
        c.grant(sentinel.whatever, sentinel.whatever)  # Nothing happens.

    def test_grant(self):
        hookenv.is_leader.return_value = True
        c = coordinator.BaseCoordinator()
        c.default_grant = MagicMock()
        c.grant_other = MagicMock()

        ts = coordinator._timestamp
        ts1, ts2 = ts(), ts()

        c.requests = {'foo/1': {'mylock': ts1, 'other': ts()},
                      'foo/2': {'mylock': ts2},
                      'foo/3': {'mylock': ts()}}
        grants = {'foo/1': {'mylock': ts1}}
        c.grants = grants.copy()

        # foo/1 already has a granted mylock, so returns True.
        self.assertTrue(c.grant('mylock', 'foo/1'))

        # foo/2 does not have a granted mylock. default_grant will
        # be called to make a decision (no)
        c.default_grant.return_value = False
        self.assertFalse(c.grant('mylock', 'foo/2'))
        self.assertDictEqual(grants, c.grants)
        c.default_grant.assert_called_once_with('mylock', 'foo/2',
                                                set(['foo/1']),
                                                ['foo/2', 'foo/3'])
        c.default_grant.reset_mock()

        # Lets say yes.
        c.default_grant.return_value = True
        self.assertTrue(c.grant('mylock', 'foo/2'))
        grants = {'foo/1': {'mylock': ts1}, 'foo/2': {'mylock': ts2}}
        self.assertDictEqual(grants, c.grants)
        c.default_grant.assert_called_once_with('mylock', 'foo/2',
                                                set(['foo/1']),
                                                ['foo/2', 'foo/3'])

        # The other lock has custom logic, in the form of the overridden
        # grant_other method.
        c.grant_other.return_value = False
        self.assertFalse(c.grant('other', 'foo/1'))
        c.grant_other.assert_called_once_with('other', 'foo/1',
                                              set(), ['foo/1'])

        # If there is no request, grant returns False
        c.grant_other.return_value = True
        self.assertFalse(c.grant('other', 'foo/2'))

    def test_released(self):
        c = coordinator.BaseCoordinator()
        with patch.object(c, 'msg') as msg:
            c.released('foo/2', 'mylock', coordinator._utcnow())
            expected = 'Leader released mylock from foo/2, held 0:01:00'
            msg.assert_called_once_with(expected)

    def test_require(self):
        c = coordinator.BaseCoordinator()
        c.acquire = MagicMock()
        c.granted = MagicMock()
        guard = MagicMock()

        wrapped = MagicMock()

        @c.require('mylock', guard)
        def func(*args, **kw):
            wrapped(*args, **kw)

        # If the lock is granted, the wrapped function is called.
        c.granted.return_value = True
        func(arg=True)
        wrapped.assert_called_once_with(arg=True)
        wrapped.reset_mock()

        # If the lock is not granted, and the guard returns False,
        # the lock is not acquired.
        c.acquire.return_value = False
        c.granted.return_value = False
        guard.return_value = False
        func()
        self.assertFalse(wrapped.called)
        self.assertFalse(c.acquire.called)

        # If the lock is not granted, and the guard returns True,
        # the lock is acquired. But the function still isn't called if
        # it cannot be acquired immediately.
        guard.return_value = True
        func()
        self.assertFalse(wrapped.called)
        c.acquire.assert_called_once_with('mylock')

        # Finally, if the lock is not granted, and the guard returns True,
        # and the lock acquired immediately, the function is called.
        c.acquire.return_value = True
        func(sentinel.arg)
        wrapped.assert_called_once_with(sentinel.arg)

    def test_msg(self):
        c = coordinator.BaseCoordinator()
        # Just a wrapper around hookenv.log
        c.msg('hi')
        hookenv.log.assert_called_once_with('coordinator.BaseCoordinator hi',
                                            level=hookenv.INFO)

    def test_name(self):
        # We use the class name in a few places to avoid conflicts.
        # We assume we won't be using multiple BaseCoordinator subclasses
        # with the same name at the same time.
        c = coordinator.BaseCoordinator()
        self.assertEqual(c._name(), 'BaseCoordinator')
        c = coordinator.Serial()
        self.assertEqual(c._name(), 'Serial')

    @patch.object(hookenv, 'leader_get')
    def test_load_state(self, leader_get):
        c = coordinator.BaseCoordinator()
        unit = hookenv.local_unit()

        # c.granted is just the leader_get decoded.
        leader_get.return_value = '{"json": true}'
        c._load_state()
        self.assertDictEqual(c.grants, {'json': True})

        # With no relid, there is no peer relation so request state
        # is pulled from a local stash.
        with patch.object(c, '_load_local_state') as loc_state:
            loc_state.return_value = {'local': True}
            c._load_state()
            self.assertDictEqual(c.requests, {unit: {'local': True}})

        # With a relid, request details are pulled from the peer relation.
        # If there is no data in the peer relation from the local unit,
        # we still pull it from the local stash as it means this is the
        # first time we have joined.
        c.relid = 'cluster:1'
        with patch.object(c, '_load_local_state') as loc_state, \
                patch.object(c, '_load_peer_state') as peer_state:
            loc_state.return_value = {'local': True}
            peer_state.return_value = {'foo/2': {'mylock': 'whatever'}}
            c._load_state()
            self.assertDictEqual(c.requests, {unit: {'local': True},
                                              'foo/2': {'mylock': 'whatever'}})

        # If there are local details in the peer relation, the local
        # stash is ignored.
        with patch.object(c, '_load_local_state') as loc_state, \
                patch.object(c, '_load_peer_state') as peer_state:
            loc_state.return_value = {'local': True}
            peer_state.return_value = {unit: {},
                                       'foo/2': {'mylock': 'whatever'}}
            c._load_state()
            self.assertDictEqual(c.requests, {unit: {},
                                              'foo/2': {'mylock': 'whatever'}})

    def test_emit_state(self):
        c = coordinator.BaseCoordinator()
        unit = hookenv.local_unit()
        c.requests = {unit: {'lock_a': sentinel.ts,
                             'lock_b': sentinel.ts,
                             'lock_c': sentinel.ts}}
        c.grants = {unit: {'lock_a': sentinel.ts,
                           'lock_b': sentinel.ts2}}
        with patch.object(c, 'msg') as msg:
            c._emit_state()
            msg.assert_has_calls([call('Granted lock_a'),
                                  call('Waiting on lock_b'),
                                  call('Waiting on lock_c')],
                                 any_order=True)

    @patch.object(hookenv, 'relation_set')
    @patch.object(hookenv, 'leader_set')
    def test_save_state(self, leader_set, relation_set):
        c = coordinator.BaseCoordinator()
        unit = hookenv.local_unit()
        c.grants = {'directdump': True}
        c.requests = {unit: 'data1', 'foo/2': 'data2'}

        # grants is dumped to leadership settings, if the unit is leader.
        with patch.object(c, '_save_local_state') as save_loc:
            c._save_state()
            self.assertFalse(leader_set.called)
            hookenv.is_leader.return_value = True
            c._save_state()
            leader_set.assert_called_once_with({c.key: '{"directdump": true}'})

        # If there is no relation id, the local units requests is dumped
        # to a local stash.
        with patch.object(c, '_save_local_state') as save_loc:
            c._save_state()
            save_loc.assert_called_once_with('data1')

        # If there is a relation id, the local units requests is dumped
        # to the peer relation.
        with patch.object(c, '_save_local_state') as save_loc:
            c.relid = 'cluster:1'
            c._save_state()
            self.assertFalse(save_loc.called)
            relation_set.assert_called_once_with(
                c.relid, relation_settings={c.key: '"data1"'})  # JSON encoded

    @patch.object(hookenv, 'relation_get')
    @patch.object(hookenv, 'related_units')
    def test_load_peer_state(self, related_units, relation_get):
        # Standard relation-get loops, decoding results from JSON.
        c = coordinator.BaseCoordinator()
        c.key = sentinel.key
        c.relid = sentinel.relid
        related_units.return_value = ['foo/2', 'foo/3']
        d = {'foo/1': {'foo/1': True},
             'foo/2': {'foo/2': True},
             'foo/3': {'foo/3': True}}

        def _get(key, unit, relid):
            assert key == sentinel.key
            assert relid == sentinel.relid
            return json.dumps(d[unit])
        relation_get.side_effect = _get

        self.assertDictEqual(c._load_peer_state(), d)

    def test_local_state_filename(self):
        c = coordinator.BaseCoordinator()
        self.assertEqual(c._local_state_filename(),
                         '.charmhelpers.coordinator.BaseCoordinator')

    def test_load_local_state(self):
        c = coordinator.BaseCoordinator()
        with tempfile.NamedTemporaryFile(mode='w') as f:
            with patch.object(c, '_local_state_filename') as fn:
                fn.return_value = f.name
                d = 'some data'
                json.dump(d, f)
                f.flush()
                d2 = c._load_local_state()
                self.assertEqual(d, d2)

    def test_save_local_state(self):
        c = coordinator.BaseCoordinator()
        with tempfile.NamedTemporaryFile(mode='r') as f:
            with patch.object(c, '_local_state_filename') as fn:
                fn.return_value = f.name
                c._save_local_state('some data')
                self.assertEqual(json.load(f), 'some data')

    def test_release_granted(self):
        c = coordinator.BaseCoordinator()
        unit = hookenv.local_unit()
        c.requests = {unit: {'lock1': sentinel.ts, 'lock2': sentinel.ts},
                      'foo/2': {'lock1': sentinel.ts}}
        c.grants = {unit: {'lock1': sentinel.ts},
                    'foo/2': {'lock1': sentinel.ts}}
        # The granted lock for the local unit is released.
        c._release_granted()
        self.assertDictEqual(c.requests, {unit: {'lock2': sentinel.ts},
                                          'foo/2': {'lock1': sentinel.ts}})

    def test_implicit_peer_relation_name(self):
        self.assertEqual(coordinator._implicit_peer_relation_name(),
                         'cluster')

    def test_default_grant(self):
        c = coordinator.Serial()
        # Lock not granted. First in the queue.
        self.assertTrue(c.default_grant(sentinel.lock, sentinel.u1,
                                        set(), [sentinel.u1, sentinel.u2]))

        # Lock not granted. Later in the queue.
        self.assertFalse(c.default_grant(sentinel.lock, sentinel.u1,
                                         set(), [sentinel.u2, sentinel.u1]))

        # Lock already granted
        self.assertFalse(c.default_grant(sentinel.lock, sentinel.u1,
                                         set([sentinel.u2]), [sentinel.u1]))
