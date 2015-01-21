# -*- coding: utf-8 -*-
#
# Copyright 2015 Canonical Ltd.
#
# Authors:
#  Kapil Thangavelu <kapil.foss@gmail.com>
#
import unittest
import tempfile

from charmhelpers.core.unitdata import Storage


class StorageTest(unittest.TestCase):

    def test_init_kv_multiple(self):
        with tempfile.NamedTemporaryFile() as fh:
            kv = Storage(fh.name)
            with kv.hook_scope('xyz'):
                kv.set('x', 1)
            kv.close()

            kv = Storage(fh.name)
            with kv.hook_scope('abc'):
                self.assertEqual(kv.get('x'), 1)
            kv.close()

    def test_hook_scope(self):
        kv = Storage(':memory:')
        try:
            with kv.hook_scope('install') as rev:
                self.assertEqual(rev, 1)
                kv.set('a', 1)
                raise RuntimeError('x')
        except RuntimeError:
            self.assertEqual(kv.get('a'), None)

        with kv.hook_scope('config-changed') as rev:
            self.assertEqual(rev, 1)
            kv.set('a', 1)
        self.assertEqual(kv.get('a'), 1)

        kv.revision = None

        with kv.hook_scope('start') as rev:
            self.assertEqual(rev, 2)
            kv.set('a', False)
            kv.set('a', True)
        self.assertEqual(kv.get('a'), True)

        # History doesn't decode atm
        history = [h[:-1] for h in kv.gethistory('a')]
        self.assertEqual(
            history,
            [(1, 'a', '1', 'config-changed'),
             (2, 'a', 'true', 'start')])

    def test_delta_no_previous_and_history(self):
        kv = Storage(':memory:')
        with kv.hook_scope('install'):
            data = {'a': 0, 'c': False}
            delta = kv.delta(data, 'settings.')
            self.assertEqual(delta, {
                'a': (None, False), 'c': (None, False)})
            kv.update(data, 'settings.')

        with kv.hook_scope('config'):
            data = {'a': 1, 'c': True}
            delta = kv.delta(data, 'settings.')
            self.assertEqual(delta, {
                'a': (0, 1), 'c': (False, True)})
            kv.update(data, 'settings.')
        # strip the time
        history = [h[:-1] for h in kv.gethistory('settings.a')]
        self.assertEqual(
            history,
            [(1, 'settings.a', '0', 'install'),
             (2, 'settings.a', '1', 'config')])

    def test_delta(self):
        kv = Storage(':memory:')
        kv.update({'a': 1, 'b': 2.2}, prefix="x")
        delta = kv.delta({'a': 0, 'c': False}, prefix='x')
        self.assertEqual(
            delta,
            {'a': (1, 0), 'b': (2.2, None), 'c': (None, False)})
        self.assertEqual(delta.a.previous, 1)
        self.assertEqual(delta.a.current, 0)
        self.assertEqual(delta.c.previous, None)
        self.assertEqual(delta.a.current, False)

    def test_update(self):
        kv = Storage(':memory:')
        kv.update({'v_a': 1, 'v_b': 2.2})
        self.assertEqual(kv.getrange('v_'), {'v_a': 1, 'v_b': 2.2})

        kv.update({'a': False, 'b': True}, prefix='x_')
        self.assertEqual(
            kv.getrange('x_', True), {'a': False, 'b': True})

    def test_keyrange(self):
        kv = Storage(':memory:')
        kv.set('docker.net_mtu', 1)
        kv.set('docker.net_nack', True)
        kv.set('docker.net_type', 'vxlan')
        self.assertEqual(
            kv.getrange('docker'),
            {'docker.net_mtu': 1, 'docker.net_type': 'vxlan',
             'docker.net_nack': True})
        self.assertEqual(
            kv.getrange('docker.', True),
            {'net_mtu': 1, 'net_type': 'vxlan', 'net_nack': True})

    def test_get_set_unset(self):
        kv = Storage(':memory:')
        kv.hook_scope('test')
        kv.set('hello', 'saucy')
        kv.set('hello', 'world')
        self.assertEqual(kv.get('hello'), 'world')
        kv.flush()
        kv.unset('hello')
        self.assertEqual(kv.get('hello'), None)
        kv.flush(False)
        self.assertEqual(kv.get('hello'), 'world')

if __name__ == '__main__':
    unittest.main()
