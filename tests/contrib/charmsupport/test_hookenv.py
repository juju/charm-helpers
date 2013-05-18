from mock import MagicMock
from testtools import TestCase

from charmhelpers.contrib.charmsupport import hookenv

class HooksTest(TestCase):
    def test_runs_a_registered_function(self):
        foo = MagicMock()
        hooks = hookenv.Hooks()
        hooks.register('foo', foo)

        hooks.execute(['foo', 'some', 'other', 'args'])

        foo.assert_called_with()

    def test_cannot_run_unregistered_function(self):
        foo = MagicMock()
        hooks = hookenv.Hooks()
        hooks.register('foo', foo)

        self.assertRaises(hookenv.UnregisteredHookError, hooks.execute,
                          ['bar'])

    def test_can_run_a_decorated_function_as_one_or_more_hooks(self):
        execs = []
        hooks = hookenv.Hooks()

        @hooks.hook('bar', 'baz')
        def func():
            execs.append(True)

        hooks.execute(['bar'])
        hooks.execute(['baz'])
        self.assertRaises(hookenv.UnregisteredHookError, hooks.execute,
                          ['brew'])
        self.assertEqual(execs, [True, True])

    def test_can_run_a_decorated_function_as_itself(self):
        execs = []
        hooks = hookenv.Hooks()

        @hooks.hook()
        def func():
            execs.append(True)

        hooks.execute(['func'])
        self.assertRaises(hookenv.UnregisteredHookError, hooks.execute,
                          ['brew'])
        self.assertEqual(execs, [True])
