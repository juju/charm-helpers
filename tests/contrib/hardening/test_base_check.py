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

from mock import call
from mock import patch
from testtools import TestCase

from charmhelpers.contrib.hardening.base_checks import BaseCheck
from charmhelpers.contrib.hardening.base_checks import BaseFileCheck
from charmhelpers.contrib.hardening.base_checks import DirectoryPermissionCheck
from charmhelpers.contrib.hardening.base_checks import FilePermissionCheck


class BaseCheckTestCase(TestCase):

    def setUp(self):
        super(BaseCheckTestCase, self).setUp()

    def test__take_action_default(self):
        check = BaseCheck()
        take_action = check._take_action()
        self.assertTrue(take_action)

    def test__take_action_unless_true(self):
        check = BaseCheck(unless=True)
        take_action = check._take_action()
        self.assertFalse(take_action)

    def test__take_action_unless_false(self):
        check = BaseCheck(unless=False)
        take_action = check._take_action()
        self.assertTrue(take_action)

    def test__take_action_unless_callback_false(self):
        def callback():
            return False
        check = BaseCheck(unless=callback)
        take_action = check._take_action()
        self.assertTrue(take_action)

    def test__take_action_unless_callback_true(self):
        def callback():
            return True
        check = BaseCheck(unless=callback)
        take_action = check._take_action()
        self.assertFalse(take_action)


@patch('os.path.exists')
class BaseFileCheckTestCase(TestCase):

    def setUp(self):
        super(BaseFileCheckTestCase, self).setUp()
        self._patch_obj(BaseFileCheck, 'is_compliant')
        self._patch_obj(BaseFileCheck, 'comply')
        self._patch('charmhelpers.contrib.hardening.base_checks.log')

    def _patch_obj(self, obj, method):
        _m = patch.object(obj, method)
        mock = _m.start()
        self.addCleanup(mock.stop)
        setattr(self, method, mock)

    def _patch(self, method):
        _m = patch(method)
        mock = _m.start()
        self.addCleanup(mock.stop)
        method_name = method[method.rfind('.') + 1:]
        setattr(self, method_name, mock)

    def test_ensure_compliance(self, mock_exists):
        mock_exists.return_value = False
        check = BaseFileCheck(paths='/tmp/foo')
        check.ensure_compliance()
        self.assertFalse(self.comply.called)

    def test_ensure_compliance_in_compliance(self, mock_exists):
        mock_exists.return_value = True
        self.is_compliant.return_value = True
        check = BaseFileCheck(paths=['/tmp/foo'])
        check.ensure_compliance()
        mock_exists.assert_has_calls(call('/tmp/foo'))
        self.is_compliant.assert_has_calls(call('/tmp/foo'))
        self.assertFalse(self.log.called)
        self.assertFalse(self.comply.called)

    def test_ensure_compliance_out_of_compliance(self, mock_exists):
        mock_exists.return_value = True
        self.is_compliant.return_value = False
        check = BaseFileCheck(paths=['/tmp/foo'])
        check.ensure_compliance()
        mock_exists.assert_has_calls(call('/tmp/foo'))
        self.is_compliant.assert_has_calls(call('/tmp/foo'))
        self.assertTrue(self.log.called)
        self.comply.assert_has_calls(call('/tmp/foo'))


class EasyMock(dict):
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__


class FilePermissionCheckTestCase(TestCase):
    def setUp(self):
        super(FilePermissionCheckTestCase, self).setUp()
        self._patch('charmhelpers.contrib.hardening.base_checks.grp.getgrnam')
        self._patch('charmhelpers.contrib.hardening.base_checks.pwd.getpwnam')
        self._patch_obj(FilePermissionCheck, '_get_stat')
        self.getpwnam.return_value = EasyMock({'pw_name': 'ubuntu',
                                               'pw_uid': 1000})
        self.getgrnam.return_value = EasyMock({'gr_name': 'ubuntu',
                                               'gr_gid': 1000})
        self._get_stat.return_value = EasyMock({'st_mode': 0o644,
                                                'st_uid': 1000,
                                                'st_gid': 1000})

    def _patch_obj(self, obj, method):
        _m = patch.object(obj, method)
        mock = _m.start()
        self.addCleanup(mock.stop)
        setattr(self, method, mock)

    def _patch(self, method):
        _m = patch(method)
        mock = _m.start()
        self.addCleanup(mock.stop)
        method_name = method[method.rfind('.') + 1:]
        setattr(self, method_name, mock)

    def test_is_compliant(self):
        check = FilePermissionCheck(paths=['/foo/bar'], user='ubuntu',
                                    group='ubuntu', mode=0o644)
        compliant = check.is_compliant('/foo/bar')
        self.assertTrue(compliant)

    def test_not_compliant_wrong_group(self):
        self.getgrnam.return_value = EasyMock({'gr_name': 'admin',
                                               'gr_gid': 222})
        check = FilePermissionCheck(paths=['/foo/bar'], user='ubuntu',
                                    group='ubuntu', mode=0o644)
        compliant = check.is_compliant('/foo/bar')
        self.assertFalse(compliant)

    def test_not_compliant_wrong_user(self):
        self.getpwnam.return_value = EasyMock({'pw_name': 'fred',
                                               'pw_uid': 123})
        check = FilePermissionCheck(paths=['/foo/bar'], user='ubuntu',
                                    group='ubuntu', mode=0o644)
        compliant = check.is_compliant('/foo/bar')
        self.assertFalse(compliant)

    def test_not_compliant_wrong_permissions(self):
        self._get_stat.return_value = EasyMock({'st_mode': 0o777,
                                                'st_uid': 1000,
                                                'st_gid': 1000})
        check = FilePermissionCheck(paths=['/foo/bar'], user='ubuntu',
                                    group='ubuntu', mode=0o644)
        compliant = check.is_compliant('/foo/bar')
        self.assertFalse(compliant)

    @patch('charmhelpers.contrib.hardening.base_checks.os.chown')
    @patch('charmhelpers.contrib.hardening.base_checks.os.chmod')
    def test_comply(self, mock_chmod, mock_chown):
        check = FilePermissionCheck(paths=['/foo/bar'], user='ubuntu',
                                    group='ubuntu', mode=0o644)
        check.comply('/foo/bar')
        mock_chown.assert_has_calls(call('/foo/bar', 1000, 1000))
        mock_chmod.assert_has_calls(call('/foo/bar', 0o644))


class DirectoryPermissionCheckTestCase(TestCase):
    def setUp(self):
        super(DirectoryPermissionCheckTestCase, self).setUp()

    @patch('charmhelpers.contrib.hardening.base_checks.os.path.isdir')
    def test_is_compliant_not_directory(self, mock_isdir):
        mock_isdir.return_value = False
        check = DirectoryPermissionCheck(paths=['/foo/bar'], user='ubuntu',
                                         group='ubuntu', mode=0700)
        self.assertRaises(ValueError, check.is_compliant, '/foo/bar')

    @patch('charmhelpers.contrib.hardening.base_checks.FilePermissionCheck.'
           'is_compliant')
    @patch('charmhelpers.contrib.hardening.base_checks.os.walk')
    @patch('charmhelpers.contrib.hardening.base_checks.os.path.isdir')
    def test_is_compliant_file_not_compliant(self, mock_isdir, mock_walk,
                                             mock_parent_is_compliant):
        mock_parent_is_compliant.return_value = False
        mock_isdir.return_value = True
        mock_walk.return_value = ('/foo/bar', [], [])
        check = DirectoryPermissionCheck(paths=['/foo/bar'], user='ubuntu',
                                         group='ubuntu', mode=0700)
        compliant = check.is_compliant('/foo/bar')
        self.assertFalse(compliant)
