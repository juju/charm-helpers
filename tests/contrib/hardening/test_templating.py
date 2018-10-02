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

import tempfile
import os
import six

from mock import call, patch
from unittest import TestCase

from charmhelpers.contrib.hardening import templating
from charmhelpers.contrib.hardening import utils
from charmhelpers.contrib.hardening.audits.file import (
    TemplatedFile,
    FileContentAudit,
)
from charmhelpers.contrib.hardening.ssh.checks import (
    config as ssh_config_check
)
from charmhelpers.contrib.hardening.host.checks import (
    sysctl,
    securetty,
)
from charmhelpers.contrib.hardening.apache.checks import (
    config as apache_config_check
)
from charmhelpers.contrib.hardening.mysql.checks import (
    config as mysql_config_check
)


class TemplatingTestCase(TestCase):

    def setUp(self):
        super(TemplatingTestCase, self).setUp()

        os.environ['JUJU_CHARM_DIR'] = '/tmp'
        self.pathindex = {}
        self.addCleanup(lambda: os.environ.pop('JUJU_CHARM_DIR'))

    def get_renderers(self, audits):
        renderers = []
        for a in audits:
            if issubclass(a.__class__, TemplatedFile):
                renderers.append(a)

        return renderers

    def get_contentcheckers(self, audits):
        contentcheckers = []
        for a in audits:
            if issubclass(a.__class__, FileContentAudit):
                contentcheckers.append(a)

        return contentcheckers

    def render(self, renderers):
        for template in renderers:
            with patch.object(template, 'pre_write', lambda: None):
                with patch.object(template, 'post_write', lambda: None):
                    with patch.object(template, 'run_service_actions'):
                        with patch.object(template, 'save_checksum'):
                            for p in template.paths:
                                template.comply(p)

    def checkcontents(self, contentcheckers):
        for check in contentcheckers:
            if check.path not in self.pathindex:
                continue

            self.assertTrue(check.is_compliant(self.pathindex[check.path]))

    @patch.object(ssh_config_check, 'lsb_release',
                  lambda: {'DISTRIB_CODENAME': 'precise'})
    @patch.object(utils, 'ensure_permissions')
    @patch.object(templating, 'write')
    @patch('charmhelpers.contrib.hardening.audits.file.log')
    @patch.object(templating, 'log', lambda *args, **kwargs: None)
    @patch.object(utils, 'log', lambda *args, **kwargs: None)
    @patch.object(ssh_config_check, 'log', lambda *args, **kwargs: None)
    def test_ssh_config_render_and_check_lt_trusty(self, mock_log, mock_write,
                                                   mock_ensure_permissions):
        audits = ssh_config_check.get_audits()
        contentcheckers = self.get_contentcheckers(audits)
        renderers = self.get_renderers(audits)
        configs = {}

        def write(path, data):
            with tempfile.NamedTemporaryFile(delete=False) as ftmp:
                if os.path.basename(path) == "ssh_config":
                    configs['ssh'] = ftmp.name
                elif os.path.basename(path) == "sshd_config":
                    configs['sshd'] = ftmp.name

                if path in self.pathindex:
                    raise Exception("File already rendered '%s'" % path)

                self.pathindex[path] = ftmp.name
                with open(ftmp.name, 'wb') as fd:
                    fd.write(data)

        mock_write.side_effect = write
        self.render(renderers)
        self.checkcontents(contentcheckers)
        self.assertTrue(mock_write.called)
        args_list = mock_write.call_args_list
        self.assertEqual('/etc/ssh/ssh_config', args_list[0][0][0])
        self.assertEqual('/etc/ssh/sshd_config', args_list[1][0][0])
        self.assertEqual(mock_write.call_count, 2)

        calls = [call("Auditing contents of file '%s'" % configs['ssh'],
                      level='DEBUG'),
                 call('Checked 10 cases and 10 passed', level='DEBUG'),
                 call("Auditing contents of file '%s'" % configs['sshd'],
                      level='DEBUG'),
                 call('Checked 10 cases and 10 passed', level='DEBUG')]
        mock_log.assert_has_calls(calls)

    @patch.object(ssh_config_check, 'lsb_release',
                  lambda: {'DISTRIB_CODENAME': 'trusty'})
    @patch.object(utils, 'ensure_permissions')
    @patch.object(templating, 'write')
    @patch('charmhelpers.contrib.hardening.audits.file.log')
    @patch.object(templating, 'log', lambda *args, **kwargs: None)
    @patch.object(utils, 'log', lambda *args, **kwargs: None)
    @patch.object(ssh_config_check, 'log', lambda *args, **kwargs: None)
    def test_ssh_config_render_and_check_gte_trusty(self, mock_log, mock_write,
                                                    mock_ensure_permissions):
        audits = ssh_config_check.get_audits()
        contentcheckers = self.get_contentcheckers(audits)
        renderers = self.get_renderers(audits)

        def write(path, data):
            with tempfile.NamedTemporaryFile(delete=False) as ftmp:
                if path in self.pathindex:
                    raise Exception("File already rendered '%s'" % path)

                self.pathindex[path] = ftmp.name
                with open(ftmp.name, 'wb') as fd:
                    fd.write(data)

        mock_write.side_effect = write
        self.render(renderers)
        self.checkcontents(contentcheckers)
        self.assertTrue(mock_write.called)
        args_list = mock_write.call_args_list
        self.assertEqual('/etc/ssh/ssh_config', args_list[0][0][0])
        self.assertEqual('/etc/ssh/sshd_config', args_list[1][0][0])
        self.assertEqual(mock_write.call_count, 2)

        mock_log.assert_has_calls([call('Checked 9 cases and 9 passed',
                                        level='DEBUG')])

    @patch.object(utils, 'ensure_permissions')
    @patch.object(templating, 'write')
    @patch.object(sysctl, 'log', lambda *args, **kwargs: None)
    @patch.object(templating, 'log', lambda *args, **kwargs: None)
    @patch.object(utils, 'log', lambda *args, **kwargs: None)
    def test_os_sysctl_and_check(self, mock_write, mock_ensure_permissions):
        audits = sysctl.get_audits()
        contentcheckers = self.get_contentcheckers(audits)
        renderers = self.get_renderers(audits)

        def write(path, data):
            if path in self.pathindex:
                raise Exception("File already rendered '%s'" % path)

            with tempfile.NamedTemporaryFile(delete=False) as ftmp:
                self.pathindex[path] = ftmp.name
                with open(ftmp.name, 'wb') as fd:
                    fd.write(data)

        mock_write.side_effect = write
        self.render(renderers)
        self.checkcontents(contentcheckers)
        self.assertTrue(mock_write.called)
        args_list = mock_write.call_args_list
        self.assertEqual('/etc/sysctl.d/99-juju-hardening.conf',
                         args_list[0][0][0])
        self.assertEqual(mock_write.call_count, 1)

    @patch.object(utils, 'ensure_permissions')
    @patch.object(templating, 'write')
    @patch.object(sysctl, 'log', lambda *args, **kwargs: None)
    @patch.object(templating, 'log', lambda *args, **kwargs: None)
    @patch.object(utils, 'log', lambda *args, **kwargs: None)
    def test_os_securetty_and_check(self, mock_write, mock_ensure_permissions):
        audits = securetty.get_audits()
        contentcheckers = self.get_contentcheckers(audits)
        renderers = self.get_renderers(audits)

        def write(path, data):
            if path in self.pathindex:
                raise Exception("File already rendered '%s'" % path)

            with tempfile.NamedTemporaryFile(delete=False) as ftmp:
                self.pathindex[path] = ftmp.name
                with open(ftmp.name, 'wb') as fd:
                    fd.write(data)

        mock_write.side_effect = write
        self.render(renderers)
        self.checkcontents(contentcheckers)
        self.assertTrue(mock_write.called)
        args_list = mock_write.call_args_list
        self.assertEqual('/etc/securetty', args_list[0][0][0])
        self.assertEqual(mock_write.call_count, 1)

    @patch.object(apache_config_check.utils, 'get_settings', lambda x: {
        'common': {'apache_dir': '/tmp/foo'},
        'hardening': {
            'allowed_http_methods': {'GOGETEM'},
            'modules_to_disable': {'modfoo'},
            'traceenable': 'off',
            'servertokens': 'Prod',
            'honor_cipher_order': 'on',
            'cipher_suite': 'ALL:+MEDIUM:+HIGH:!LOW:!MD5:!RC4:!eNULL:!aNULL:!3DES'
        }
    })
    @patch('charmhelpers.contrib.hardening.audits.file.os.path.exists',
           lambda *a, **kwa: True)
    @patch.object(apache_config_check, 'subprocess')
    @patch.object(utils, 'ensure_permissions')
    @patch.object(templating, 'write')
    @patch.object(templating, 'log', lambda *args, **kwargs: None)
    @patch.object(utils, 'log', lambda *args, **kwargs: None)
    def test_apache_conf_and_check(self, mock_write, mock_ensure_permissions,
                                   mock_subprocess):
        mock_subprocess.call.return_value = 0
        apache_version = b"""Server version: Apache/2.4.7 (Ubuntu)
        Server built:   Jan 14 2016 17:45:23
        """
        mock_subprocess.check_output.return_value = apache_version
        audits = apache_config_check.get_audits()
        contentcheckers = self.get_contentcheckers(audits)
        renderers = self.get_renderers(audits)

        def write(path, data):
            if path in self.pathindex:
                raise Exception("File already rendered '%s'" % path)

            with tempfile.NamedTemporaryFile(delete=False) as ftmp:
                self.pathindex[path] = ftmp.name
                with open(ftmp.name, 'wb') as fd:
                    fd.write(data)

        mock_write.side_effect = write
        self.render(renderers)
        self.checkcontents(contentcheckers)
        self.assertTrue(mock_write.called)
        args_list = mock_write.call_args_list
        self.assertEqual('/tmp/foo/mods-available/alias.conf',
                         args_list[0][0][0])
        self.assertEqual(mock_write.call_count, 2)

    @patch.object(apache_config_check.utils, 'get_settings', lambda x: {
        'security': {},
        'hardening': {
            'mysql-conf': '/tmp/foo/mysql.cnf',
            'hardening-conf': '/tmp/foo/conf.d/hardening.cnf'
        }
    })
    @patch('charmhelpers.contrib.hardening.audits.file.os.path.exists',
           lambda *a, **kwa: True)
    @patch.object(utils, 'ensure_permissions')
    @patch.object(templating, 'write')
    @patch.object(mysql_config_check.subprocess, 'call',
                  lambda *args, **kwargs: 0)
    @patch.object(templating, 'log', lambda *args, **kwargs: None)
    @patch.object(utils, 'log', lambda *args, **kwargs: None)
    def test_mysql_conf_and_check(self, mock_write, mock_ensure_permissions):
        audits = mysql_config_check.get_audits()
        contentcheckers = self.get_contentcheckers(audits)
        renderers = self.get_renderers(audits)

        def write(path, data):
            if path in self.pathindex:
                raise Exception("File already rendered '%s'" % path)

            with tempfile.NamedTemporaryFile(delete=False) as ftmp:
                self.pathindex[path] = ftmp.name
                with open(ftmp.name, 'wb') as fd:
                    fd.write(data)

        mock_write.side_effect = write
        self.render(renderers)
        self.checkcontents(contentcheckers)
        self.assertTrue(mock_write.called)
        args_list = mock_write.call_args_list
        self.assertEqual('/tmp/foo/conf.d/hardening.cnf',
                         args_list[0][0][0])
        self.assertEqual(mock_write.call_count, 1)

    def tearDown(self):
        # Cleanup
        for path in six.itervalues(self.pathindex):
            os.remove(path)

        super(TemplatingTestCase, self).tearDown()
