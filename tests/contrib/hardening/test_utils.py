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

import six
import tempfile

from mock import (
    MagicMock,
    call,
    patch
)
from unittest import TestCase

from charmhelpers.contrib.hardening import utils


class UtilsTestCase(TestCase):

    def setUp(self):
        super(UtilsTestCase, self).setUp()
        utils.__SETTINGS__ = {}

    @patch.object(utils.grp, 'getgrnam')
    @patch.object(utils.pwd, 'getpwnam')
    @patch.object(utils, 'os')
    @patch.object(utils, 'log', lambda *args, **kwargs: None)
    def test_ensure_permissions(self, mock_os, mock_getpwnam, mock_getgrnam):
        user = MagicMock()
        user.pw_uid = '12'
        mock_getpwnam.return_value = user
        group = MagicMock()
        group.gr_gid = '23'
        mock_getgrnam.return_value = group

        with tempfile.NamedTemporaryFile() as tmp:
            utils.ensure_permissions(tmp.name, 'testuser', 'testgroup', 0o0440)

        mock_getpwnam.assert_has_calls([call('testuser')])
        mock_getgrnam.assert_has_calls([call('testgroup')])
        mock_os.chown.assert_has_calls([call(tmp.name, '12', '23')])
        mock_os.chmod.assert_has_calls([call(tmp.name, 0o0440)])

    @patch.object(utils, '_get_user_provided_overrides')
    def test_settings_cache(self, mock_get_user_provided_overrides):
        mock_get_user_provided_overrides.return_value = {}
        self.assertEqual(utils.__SETTINGS__, {})
        self.assertTrue('sysctl' in utils.get_settings('os'))
        self.assertEqual(list(six.iterkeys(utils.__SETTINGS__)), ['os'])
        self.assertTrue('server' in utils.get_settings('ssh'))
        self.assertEqual(list(six.iterkeys(utils.__SETTINGS__)), ['os', 'ssh'])
