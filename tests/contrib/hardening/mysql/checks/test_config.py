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

from unittest import TestCase

from mock import patch

from charmhelpers.contrib.hardening.mysql.checks import config


class MySQLConfigTestCase(TestCase):

    @patch.object(config.subprocess, 'call', lambda *args, **kwargs: 0)
    @patch.object(config.utils, 'get_settings', lambda x: {
        'hardening': {
            'mysql-conf': {},
            'hardening-conf': {}
        }
    })
    def test_get_audits(self):
        audits = config.get_audits()
        self.assertEqual(3, len(audits))
