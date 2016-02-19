import tempfile

from mock import call, patch
from testtools import TestCase

from charmhelpers.contrib.hardening import utils


class UtilsTestCase(TestCase):

    def setUp(self):
        super(UtilsTestCase, self).setUp()

    @patch.object(utils.pwd, 'getpwnam')
    @patch.object(utils, 'os')
    def test_ensure_permissions(self, mock_os, mock_pwd):
        #mock_pwd.pw_uid.return_value = '12'
        #mock_pwd.pw_gid.return_value = '23'
        #with tempfile.NamedTemporaryFile() as tmp:
        #    utils.ensure_permissions(tmp.name, 'testuser', 0o0440)

        #mock_pwd.assert_has_calls([call('testuser')])
        #mock_os.chown.assert_has_calls([call(tmp.name, '12', '23')])
        #mock_os.chmod.assert_has_calls([call(tmp.name, 0o0440)])
        pass
