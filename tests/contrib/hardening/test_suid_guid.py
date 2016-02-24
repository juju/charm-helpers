import tempfile

from mock import (
    call,
    patch
)
from testtools import TestCase

from charmhelpers.contrib.hardening import utils

from charmhelpers.contrib.hardening.os_hardening import suid_guid


class SUIDGUIDTestCase(TestCase):

    def setUp(self):
        super(SUIDGUIDTestCase, self).setUp()

    @patch.object(suid_guid, 'log', lambda *args, **kwargs: None)
    @patch.object(suid_guid, 'subprocess')
    @patch.object(utils, 'get_defaults')
    def test_suid_guid_harden(self, mock_get_defaults, mock_subprocess):
        mock_get_defaults.return_value = {}
        p = mock_subprocess.Popen.return_value
        with tempfile.NamedTemporaryFile() as tmp:
            p.communicate.return_value = (tmp.name, "stderr")
            suid_guid.suid_guid_harden()

        cmd = ['find', '/', '-perm', '-4000', '-o', '-perm', '-2000', '-type',
               'f', '!', '-path', '/proc/*', '-print']
        calls = [call(cmd, stderr=mock_subprocess.PIPE,
                      stdout=mock_subprocess.PIPE)]
        mock_subprocess.Popen.assert_has_calls(calls)
        mock_subprocess.check_call.assert_has_call(call(['chmod', '-s',
                                                         '/tmp/tmppX3eMO']))
