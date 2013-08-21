from mock import patch
from testtools import TestCase

from charmhelpers.contrib.templating.pyformat import render
from charmhelpers.core import hookenv


class PyFormatTest(TestCase):
    @patch.object(hookenv, 'execution_environment')
    def test_renders_using_environment(self, execution_environment):
        execution_environment.return_value = {
            'foo': 'FOO',
        }

        self.assertEqual(render('foo is {foo}'), 'foo is FOO')

    @patch.object(hookenv, 'execution_environment')
    def test_extra_overrides(self, execution_environment):
        execution_environment.return_value = {
            'foo': 'FOO',
        }

        extra = {'foo': 'BAR'}

        self.assertEqual(render('foo is {foo}', extra=extra), 'foo is BAR')

    @patch.object(hookenv, 'execution_environment')
    def test_kwargs_overrides(self, execution_environment):
        execution_environment.return_value = {
            'foo': 'FOO',
        }

        extra = {'foo': 'BAR'}

        self.assertEqual(
            render('foo is {foo}', extra=extra, foo='BAZ'), 'foo is BAZ')
