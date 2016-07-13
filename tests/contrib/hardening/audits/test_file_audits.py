# Copyright 2016 Canonical Limited.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import shutil
import tempfile

from mock import call, patch

from unittest import TestCase

from charmhelpers.core import unitdata
from charmhelpers.contrib.hardening.audits import file


@patch('os.path.exists')
class BaseFileAuditTestCase(TestCase):

    def setUp(self):
        super(BaseFileAuditTestCase, self).setUp()
        self._patch_obj(file.BaseFileAudit, 'is_compliant')
        self._patch_obj(file.BaseFileAudit, 'comply')
        self._patch_obj(file, 'log')

    def _patch_obj(self, obj, method):
        _m = patch.object(obj, method)
        mock = _m.start()
        self.addCleanup(_m.stop)
        setattr(self, method, mock)

    def test_ensure_compliance(self, mock_exists):
        mock_exists.return_value = False
        check = file.BaseFileAudit(paths='/tmp/foo')
        check.ensure_compliance()
        self.assertFalse(self.comply.called)

    def test_ensure_compliance_in_compliance(self, mock_exists):
        mock_exists.return_value = True
        self.is_compliant.return_value = True
        check = file.BaseFileAudit(paths=['/tmp/foo'])
        check.ensure_compliance()
        mock_exists.assert_has_calls([call('/tmp/foo')])
        self.is_compliant.assert_has_calls([call('/tmp/foo')])
        self.assertFalse(self.log.called)
        self.assertFalse(self.comply.called)

    def test_ensure_compliance_out_of_compliance(self, mock_exists):
        mock_exists.return_value = True
        self.is_compliant.return_value = False
        check = file.BaseFileAudit(paths=['/tmp/foo'])
        check.ensure_compliance()
        mock_exists.assert_has_calls([call('/tmp/foo')])
        self.is_compliant.assert_has_calls([call('/tmp/foo')])
        self.assertTrue(self.log.called)
        self.comply.assert_has_calls([call('/tmp/foo')])


class EasyMock(dict):
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__


class FilePermissionAuditTestCase(TestCase):
    def setUp(self):
        super(FilePermissionAuditTestCase, self).setUp()
        self._patch_obj(file.grp, 'getgrnam')
        self._patch_obj(file.pwd, 'getpwnam')
        self._patch_obj(file.FilePermissionAudit, '_get_stat')
        self.getpwnam.return_value = EasyMock({'pw_name': 'testuser',
                                               'pw_uid': 1000})
        self.getgrnam.return_value = EasyMock({'gr_name': 'testgroup',
                                               'gr_gid': 1000})
        self._get_stat.return_value = EasyMock({'st_mode': 0o644,
                                                'st_uid': 1000,
                                                'st_gid': 1000})

    def _patch_obj(self, obj, method):
        _m = patch.object(obj, method)
        mock = _m.start()
        self.addCleanup(_m.stop)
        setattr(self, method, mock)

    def test_is_compliant(self):
        check = file.FilePermissionAudit(paths=['/foo/bar'],
                                         user='testuser',
                                         group='testgroup', mode=0o644)
        compliant = check.is_compliant('/foo/bar')
        self.assertTrue(compliant)

    @patch.object(file, 'log', lambda *args, **kwargs: None)
    def test_not_compliant_wrong_group(self):
        self.getgrnam.return_value = EasyMock({'gr_name': 'testgroup',
                                               'gr_gid': 222})
        check = file.FilePermissionAudit(paths=['/foo/bar'], user='testuser',
                                         group='testgroup', mode=0o644)
        compliant = check.is_compliant('/foo/bar')
        self.assertFalse(compliant)

    @patch.object(file, 'log', lambda *args, **kwargs: None)
    def test_not_compliant_wrong_user(self):
        self.getpwnam.return_value = EasyMock({'pw_name': 'fred',
                                               'pw_uid': 123})
        check = file.FilePermissionAudit(paths=['/foo/bar'], user='testuser',
                                         group='testgroup', mode=0o644)
        compliant = check.is_compliant('/foo/bar')
        self.assertFalse(compliant)

    @patch.object(file, 'log', lambda *args, **kwargs: None)
    def test_not_compliant_wrong_permissions(self):
        self._get_stat.return_value = EasyMock({'st_mode': 0o777,
                                                'st_uid': 1000,
                                                'st_gid': 1000})
        check = file.FilePermissionAudit(paths=['/foo/bar'], user='testuser',
                                         group='testgroup', mode=0o644)
        compliant = check.is_compliant('/foo/bar')
        self.assertFalse(compliant)

    @patch('charmhelpers.contrib.hardening.utils.ensure_permissions')
    @patch.object(file, 'log', lambda *args, **kwargs: None)
    def test_comply(self, _ensure_permissions):
        check = file.FilePermissionAudit(paths=['/foo/bar'], user='testuser',
                                         group='testgroup', mode=0o644)
        check.comply('/foo/bar')
        c = call('/foo/bar', 'testuser', 'testgroup', 0o644)
        _ensure_permissions.assert_has_calls([c])


class DirectoryPermissionAuditTestCase(TestCase):
    def setUp(self):
        super(DirectoryPermissionAuditTestCase, self).setUp()

    @patch('charmhelpers.contrib.hardening.audits.file.os.path.isdir')
    @patch.object(file, 'log', lambda *args, **kwargs: None)
    def test_is_compliant_not_directory(self, mock_isdir):
        mock_isdir.return_value = False
        check = file.DirectoryPermissionAudit(paths=['/foo/bar'],
                                              user='testuser',
                                              group='testgroup', mode=0o0700)
        self.assertRaises(ValueError, check.is_compliant, '/foo/bar')

    @patch.object(file.FilePermissionAudit, 'is_compliant')
    @patch.object(file, 'log', lambda *args, **kwargs: None)
    def test_is_compliant_file_not_compliant(self, mock_is_compliant):
        mock_is_compliant.return_value = False
        tmpdir = tempfile.mkdtemp()
        try:
            check = file.DirectoryPermissionAudit(paths=[tmpdir],
                                                  user='testuser',
                                                  group='testgroup',
                                                  mode=0o0700)
            compliant = check.is_compliant(tmpdir)
            self.assertFalse(compliant)
        finally:
            shutil.rmtree(tmpdir)


class NoSUIDGUIDAuditTestCase(TestCase):
    def setUp(self):
        super(NoSUIDGUIDAuditTestCase, self).setUp()

    @patch.object(file.NoSUIDSGIDAudit, '_get_stat')
    @patch.object(file, 'log', lambda *args, **kwargs: None)
    def test_is_compliant(self, mock_get_stat):
        mock_get_stat.return_value = EasyMock({'st_mode': 0o0644,
                                               'st_uid': 0,
                                               'st_gid': 0})
        audit = file.NoSUIDSGIDAudit('/foo/bar')
        compliant = audit.is_compliant('/foo/bar')
        self.assertTrue(compliant)

    @patch.object(file.NoSUIDSGIDAudit, '_get_stat')
    @patch.object(file, 'log', lambda *args, **kwargs: None)
    def test_is_noncompliant(self, mock_get_stat):
        mock_get_stat.return_value = EasyMock({'st_mode': 0o6644,
                                               'st_uid': 0,
                                               'st_gid': 0})
        audit = file.NoSUIDSGIDAudit('/foo/bar')
        compliant = audit.is_compliant('/foo/bar')
        self.assertFalse(compliant)

    @patch.object(file, 'log')
    @patch.object(file, 'check_output')
    def test_comply(self, mock_check_output, mock_log):
        audit = file.NoSUIDSGIDAudit('/foo/bar')
        audit.comply('/foo/bar')
        mock_check_output.assert_has_calls([call(['chmod', '-s', '/foo/bar'])])
        self.assertTrue(mock_log.called)


class TemplatedFileTestCase(TestCase):
    def setUp(self):
        super(TemplatedFileTestCase, self).setUp()
        self.kv = patch.object(unitdata, 'kv')
        self.kv.start()
        self.addCleanup(self.kv.stop)

    @patch.object(file.TemplatedFile, 'templates_match')
    @patch.object(file.TemplatedFile, 'contents_match')
    @patch.object(file.TemplatedFile, 'permissions_match')
    @patch.object(file, 'log', lambda *args, **kwargs: None)
    def test_is_not_compliant(self, contents_match_, permissions_match_,
                              templates_match_):
        contents_match_.return_value = False
        permissions_match_.return_value = False
        templates_match_.return_value = False

        f = file.TemplatedFile('/foo/bar', None, '/tmp', 0o0644)
        compliant = f.is_compliant('/foo/bar')
        self.assertFalse(compliant)

    @patch.object(file.TemplatedFile, 'templates_match')
    @patch.object(file.TemplatedFile, 'contents_match')
    @patch.object(file.TemplatedFile, 'permissions_match')
    @patch.object(file, 'log', lambda *args, **kwargs: None)
    def test_is_compliant(self, contents_match_, permissions_match_,
                          templates_match_):
        contents_match_.return_value = True
        permissions_match_.return_value = True
        templates_match_.return_value = True

        f = file.TemplatedFile('/foo/bar', None, '/tmp', 0o0644)
        compliant = f.is_compliant('/foo/bar')
        self.assertTrue(compliant)

    @patch.object(file.TemplatedFile, 'templates_match')
    @patch.object(file.TemplatedFile, 'contents_match')
    @patch.object(file.TemplatedFile, 'permissions_match')
    @patch.object(file, 'log', lambda *args, **kwargs: None)
    def test_template_changes(self, contents_match_, permissions_match_,
                              templates_match_):
        contents_match_.return_value = True
        permissions_match_.return_value = True
        templates_match_.return_value = False

        f = file.TemplatedFile('/foo/bar', None, '/tmp', 0o0644)
        compliant = f.is_compliant('/foo/bar')
        self.assertFalse(compliant)

    @patch.object(file, 'render_and_write')
    @patch.object(file.utils, 'ensure_permissions')
    @patch.object(file, 'log', lambda *args, **kwargs: None)
    def test_comply(self, mock_ensure_permissions, mock_render_and_write):
        class Context(object):
            def __call__(self):
                return {}
        with tempfile.NamedTemporaryFile() as ftmp:
            f = file.TemplatedFile(ftmp.name, Context(),
                                   os.path.dirname(ftmp.name), 0o0644)
            f.comply(ftmp.name)
            calls = [call(os.path.dirname(ftmp.name), ftmp.name, {})]
            mock_render_and_write.assert_has_calls(calls)
            mock_ensure_permissions.assert_has_calls([call(ftmp.name, 'root',
                                                           'root', 0o0644)])


CONTENTS_PASS = """Ciphers aes256-ctr,aes192-ctr,aes128-ctr
MACs hmac-sha2-512,hmac-sha2-256,hmac-ripemd160
KexAlgorithms diffie-hellman-group-exchange-sha256
"""


CONTENTS_FAIL = """Ciphers aes256-ctr,aes192-ctr,aes128-ctr
MACs hmac-sha2-512,hmac-sha2-256,hmac-ripemd160
KexAlgorithms diffie-hellman-group-exchange-sha256,diffie-hellman-group14-sha1,diffie-hellman-group-exchange-sha1,diffie-hellman-group1-sha1
"""


class FileContentAuditTestCase(TestCase):

    @patch.object(file, 'log')
    def test_audit_contents_pass(self, mock_log):
        conditions = {'pass':
                      [r'^KexAlgorithms\s+diffie-hellman-group-exchange-'
                       'sha256$'],
                      'fail': [r'^KexAlgorithms\s+diffie-hellman-group-'
                               'exchange-sha256.+$']}
        with tempfile.NamedTemporaryFile() as ftmp:
            filename = ftmp.name
            with open(filename, 'w') as fd:
                fd.write(CONTENTS_FAIL)

            audit = file.FileContentAudit(filename, conditions)
            self.assertFalse(audit.is_compliant(filename))

        calls = [call("Auditing contents of file '%s'" % filename,
                      level='DEBUG'),
                 call("Pattern '^KexAlgorithms\\s+diffie-hellman-group-"
                      "exchange-sha256$' was expected to pass but instead it "
                      "failed", level='WARNING'),
                 call("Pattern '^KexAlgorithms\\s+diffie-hellman-group-"
                      "exchange-sha256.+$' was expected to fail but instead "
                      "it passed", level='WARNING'),
                 call('Checked 2 cases and 0 passed', level='DEBUG')]
        mock_log.assert_has_calls(calls)

    @patch.object(file, 'log')
    def test_audit_contents_fail(self, mock_log):
        conditions = {'pass':
                      [r'^KexAlgorithms\s+diffie-hellman-group-exchange-'
                       'sha256$'],
                      'fail':
                      [r'^KexAlgorithms\s+diffie-hellman-group-exchange-'
                       'sha256.+$']}
        with tempfile.NamedTemporaryFile() as ftmp:
            filename = ftmp.name
            with open(filename, 'w') as fd:
                fd.write(CONTENTS_FAIL)

            audit = file.FileContentAudit(filename, conditions)
            self.assertFalse(audit.is_compliant(filename))

        calls = [call("Auditing contents of file '%s'" % filename,
                      level='DEBUG'),
                 call("Pattern '^KexAlgorithms\\s+diffie-hellman-group-"
                      "exchange-sha256$' was expected to pass but instead "
                      "it failed",
                      level='WARNING'),
                 call("Pattern '^KexAlgorithms\\s+diffie-hellman-group-"
                      "exchange-sha256.+$' was expected to fail but instead "
                      "it passed",
                      level='WARNING'),
                 call('Checked 2 cases and 0 passed', level='DEBUG')]
        mock_log.assert_has_calls(calls)
