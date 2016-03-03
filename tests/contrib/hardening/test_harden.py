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
from testtools import TestCase

from charmhelpers.contrib.hardening import harden
from charmhelpers.contrib.hardening.host import harden as harden_host
from charmhelpers.contrib.hardening.ssh import harden as harden_ssh
from charmhelpers.contrib.hardening.apache import harden as harden_apache
from charmhelpers.contrib.hardening.mysql import harden as harden_mysql


class HardenTestCase(TestCase):

    def setUp(self):
        super(HardenTestCase, self).setUp()

    @patch.object(harden_host, 'harden_os')
    @patch.object(harden_mysql, 'harden_mysql')
    @patch.object(harden_apache, 'harden_apache')
    @patch.object(harden_ssh, 'harden_ssh')
    @patch.object(harden, 'log', lambda *args: None)
    def test_harden(self, mock_ssh, mock_apache, mock_mysql, mock_host):
        mock_ssh.__name__ = 'ssh'
        mock_mysql.__name__ = 'mysql'
        mock_apache.__name__ = 'apache'
        mock_host.__name__ = 'host'

        @harden.harden(overrides=['ssh', 'mysql'])
        def foo(arg1, kwarg1=None):
            return "done."

        self.assertEqual(foo('anarg', kwarg1='akwarg'), "done.")
        self.assertTrue(mock_ssh.called)
        self.assertTrue(mock_mysql.called)
        self.assertFalse(mock_apache.called)
        self.assertFalse(mock_host.called)
