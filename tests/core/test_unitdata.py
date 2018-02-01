# -*- coding: utf-8 -*-
#
# Copyright 2015 Canonical Ltd.
#
# Authors:
#  Kapil Thangavelu <kapil.foss@gmail.com>
#
try:
    from StringIO import StringIO
except Exception:
    from io import StringIO

import os
import shutil
import tempfile
import unittest

from mock import patch

from charmhelpers.core.unitdata import Storage, HookData, kv


class HookDataTest(unittest.TestCase):

    def setUp(self):
        self.charm_dir = tempfile.mkdtemp()
        self.addCleanup(lambda: shutil.rmtree(self.charm_dir))
        self.change_environment(CHARM_DIR=self.charm_dir)

    def change_environment(self, **kw):
        original_env = dict(os.environ)

        @self.addCleanup
        def cleanup_env():
            os.environ.clear()
            os.environ.update(original_env)

        os.environ.update(kw)

    @patch('charmhelpers.core.hookenv.hook_name')
    @patch('charmhelpers.core.hookenv.execution_environment')
    @patch('charmhelpers.core.hookenv.charm_dir')
    def test_hook_data_records(self, cdir, ctx, name):
        name.return_value = 'config-changed'
        ctx.return_value = {
            'rels': {}, 'conf': {'a': 1}, 'env': {}, 'unit': 'someunit'}
        cdir.return_value = self.charm_dir
        with open(os.path.join(self.charm_dir, 'revision'), 'w') as fh:
            fh.write('1')
        hook_data = HookData()

        with hook_data():
            self.assertEqual(kv(), hook_data.kv)
            self.assertEqual(kv().get('charm_revisions'), ['1'])
            self.assertEqual(kv().get('unit'), 'someunit')
            self.assertEqual(list(hook_data.conf), ['a'])
            self.assertEqual(tuple(hook_data.conf.a), (None, 1))


class StorageTest(unittest.TestCase):

    def test_init_kv_multiple(self):
        with tempfile.NamedTemporaryFile() as fh:
            kv = Storage(fh.name)
            with kv.hook_scope('xyz'):
                kv.set('x', 1)
            kv.close()
            self.assertEqual(os.stat(fh.name).st_mode & 0o777, 0o600)

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

        # History doesn't decode values by default
        history = [h[:-1] for h in kv.gethistory('a')]
        self.assertEqual(
            history,
            [(1, 'a', '1', 'config-changed'),
             (2, 'a', 'true', 'start')])

        history = [h[:-1] for h in kv.gethistory('a', deserialize=True)]
        self.assertEqual(
            history,
            [(1, 'a', 1, 'config-changed'),
             (2, 'a', True, 'start')])

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

    def test_unset(self):
        kv = Storage(':memory:')
        with kv.hook_scope('install'):
            kv.set('a', True)
        with kv.hook_scope('start'):
            kv.set('a', False)
        with kv.hook_scope('config-changed'):
            kv.unset('a')
        history = [h[:-1] for h in kv.gethistory('a')]

        self.assertEqual(history, [
            (1, 'a', 'true', 'install'),
            (2, 'a', 'false', 'start'),
            (3, 'a', '"DELETED"', "config-changed")])

    def test_flush_and_close_on_closed(self):
        kv = Storage(':memory:')
        kv.close()
        kv.flush(False)
        kv.close()

    def test_multi_value_set_skips(self):
        # pure coverage test
        kv = Storage(':memory:')
        kv.set('x', 1)
        self.assertEqual(kv.set('x', 1), 1)

    def test_debug(self):
        # pure coverage test...
        io = StringIO()
        kv = Storage(':memory:')
        kv.debug(io)

    def test_record(self):
        kv = Storage(':memory:')
        kv.set('config', {'x': 1, 'b': False})
        config = kv.get('config', record=True)
        self.assertEqual(config.b, False)
        self.assertEqual(config.x, 1)
        self.assertEqual(kv.set('config.x', 1), 1)
        try:
            config.z
        except AttributeError:
            pass
        else:
            self.fail('attribute error should fire on nonexistant')

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
