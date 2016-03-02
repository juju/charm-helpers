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
import shutil
import tempfile

from mock import call
from mock import patch

from testtools import TestCase
from charmhelpers.contrib.hardening.audits.file import BaseFileAudit
from charmhelpers.contrib.hardening.audits.file import FilePermissionAudit
from charmhelpers.contrib.hardening.audits.file import DirectoryPermissionAudit
from charmhelpers.contrib.hardening.audits.file import NoSUIDGUIDAudit


@patch('os.path.exists')
class BaseFileAuditTestCase(TestCase):

    def setUp(self):
        super(BaseFileAuditTestCase, self).setUp()
        self._patch_obj(BaseFileAudit, 'is_compliant')
        self._patch_obj(BaseFileAudit, 'comply')
        self._patch('charmhelpers.contrib.hardening.audits.file.log')

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
        check = BaseFileAudit(paths='/tmp/foo')
        check.ensure_compliance()
        self.assertFalse(self.comply.called)

    def test_ensure_compliance_in_compliance(self, mock_exists):
        mock_exists.return_value = True
        self.is_compliant.return_value = True
        check = BaseFileAudit(paths=['/tmp/foo'])
        check.ensure_compliance()
        mock_exists.assert_has_calls(call('/tmp/foo'))
        self.is_compliant.assert_has_calls(call('/tmp/foo'))
        self.assertFalse(self.log.called)
        self.assertFalse(self.comply.called)

    def test_ensure_compliance_out_of_compliance(self, mock_exists):
        mock_exists.return_value = True
        self.is_compliant.return_value = False
        check = BaseFileAudit(paths=['/tmp/foo'])
        check.ensure_compliance()
        mock_exists.assert_has_calls(call('/tmp/foo'))
        self.is_compliant.assert_has_calls(call('/tmp/foo'))
        self.assertTrue(self.log.called)
        self.comply.assert_has_calls(call('/tmp/foo'))


class EasyMock(dict):
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__


class FilePermissionAuditTestCase(TestCase):
    def setUp(self):
        super(FilePermissionAuditTestCase, self).setUp()
        self._patch('charmhelpers.contrib.hardening.audits.file.grp.getgrnam')
        self._patch('charmhelpers.contrib.hardening.audits.file.pwd.getpwnam')
        self._patch_obj(FilePermissionAudit, '_get_stat')
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
        check = FilePermissionAudit(paths=['/foo/bar'],
                                    user='ubuntu',
                                    group='ubuntu', mode=0o644)
        compliant = check.is_compliant('/foo/bar')
        self.assertTrue(compliant)

    def test_not_compliant_wrong_group(self):
        self.getgrnam.return_value = EasyMock({'gr_name': 'admin',
                                               'gr_gid': 222})
        check = FilePermissionAudit(paths=['/foo/bar'], user='ubuntu',
                                    group='ubuntu', mode=0o644)
        compliant = check.is_compliant('/foo/bar')
        self.assertFalse(compliant)

    def test_not_compliant_wrong_user(self):
        self.getpwnam.return_value = EasyMock({'pw_name': 'fred',
                                               'pw_uid': 123})
        check = FilePermissionAudit(paths=['/foo/bar'], user='ubuntu',
                                    group='ubuntu', mode=0o644)
        compliant = check.is_compliant('/foo/bar')
        self.assertFalse(compliant)

    def test_not_compliant_wrong_permissions(self):
        self._get_stat.return_value = EasyMock({'st_mode': 0o777,
                                                'st_uid': 1000,
                                                'st_gid': 1000})
        check = FilePermissionAudit(paths=['/foo/bar'], user='ubuntu',
                                    group='ubuntu', mode=0o644)
        compliant = check.is_compliant('/foo/bar')
        self.assertFalse(compliant)

    @patch('charmhelpers.contrib.hardening.audits.file.os.chown')
    @patch('charmhelpers.contrib.hardening.audits.file.os.chmod')
    def test_comply(self, mock_chmod, mock_chown):
        check = FilePermissionAudit(paths=['/foo/bar'], user='ubuntu',
                                    group='ubuntu', mode=0o644)
        check.comply('/foo/bar')
        mock_chown.assert_has_calls(call('/foo/bar', 1000, 1000))
        mock_chmod.assert_has_calls(call('/foo/bar', 0o644))


class DirectoryPermissionAuditTestCase(TestCase):
    def setUp(self):
        super(DirectoryPermissionAuditTestCase, self).setUp()

    @patch('charmhelpers.contrib.hardening.audits.file.os.path.isdir')
    def test_is_compliant_not_directory(self, mock_isdir):
        mock_isdir.return_value = False
        check = DirectoryPermissionAudit(paths=['/foo/bar'], user='ubuntu',
                                         group='ubuntu', mode=0o0700)
        self.assertRaises(ValueError, check.is_compliant, '/foo/bar')

    @patch.object(FilePermissionAudit, 'is_compliant')
    def test_is_compliant_file_not_compliant(self, mock_is_compliant):
        mock_is_compliant.return_value = False
        tmpdir = tempfile.mkdtemp()
        try:
            check = DirectoryPermissionAudit(paths=[tmpdir], user='ubuntu',
                                             group='ubuntu', mode=0o0700)
            compliant = check.is_compliant(tmpdir)
            self.assertFalse(compliant)
        finally:
            shutil.rmtree(tmpdir)


class NoSUIDGUIDAuditTestCase(TestCase):
    def setUp(self):
        super(NoSUIDGUIDAuditTestCase, self).setUp()

    @patch.object(NoSUIDGUIDAudit, '_get_stat')
    def test_is_compliant(self, mock_get_stat):
        mock_get_stat.return_value = EasyMock({'st_mode': 0o0644,
                                               'st_uid': 0,
                                               'st_gid': 0})
        audit = NoSUIDGUIDAudit('/foo/bar')
        compliant = audit.is_compliant('/foo/bar')
        self.assertTrue(compliant)

    @patch.object(NoSUIDGUIDAudit, '_get_stat')
    def test_is_noncompliant(self, mock_get_stat):
        mock_get_stat.return_value = EasyMock({'st_mode': 0o6644,
                                               'st_uid': 0,
                                               'st_gid': 0})
        audit = NoSUIDGUIDAudit('/foo/bar')
        compliant = audit.is_compliant('/foo/bar')
        self.assertFalse(compliant)

    @patch('charmhelpers.contrib.hardening.audits.file.log')
    @patch('charmhelpers.contrib.hardening.audits.file.check_output')
    def test_comply(self, mock_check_output, mock_log):
        audit = NoSUIDGUIDAudit('/foo/bar')
        audit.comply('/foo/bar')
        mock_check_output.assert_has_calls(call(['chmod', '-s', '/foo/bar']))
