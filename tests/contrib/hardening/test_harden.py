# Copyright 2016 Canonical Limited.
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

from mock import patch
from unittest import TestCase

from charmhelpers.contrib.hardening import harden


class HardenTestCase(TestCase):

    def setUp(self):
        super(HardenTestCase, self).setUp()

    @patch.object(harden, 'run_apache_checks')
    @patch.object(harden, 'run_mysql_checks')
    @patch.object(harden, 'run_ssh_checks')
    @patch.object(harden, 'run_os_checks')
    @patch.object(harden, 'log', lambda *args, **kwargs: None)
    def test_harden(self, mock_host, mock_ssh, mock_mysql, mock_apache):
        mock_host.__name__ = 'host'
        mock_ssh.__name__ = 'ssh'
        mock_mysql.__name__ = 'mysql'
        mock_apache.__name__ = 'apache'

        @harden.harden(overrides=['ssh', 'mysql'])
        def foo(arg1, kwarg1=None):
            return "done."

        self.assertEqual(foo('anarg', kwarg1='akwarg'), "done.")
        self.assertTrue(mock_ssh.called)
        self.assertTrue(mock_mysql.called)
        self.assertFalse(mock_apache.called)
        self.assertFalse(mock_host.called)
