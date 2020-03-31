import charmhelpers.contrib.network.ovs.utils as utils

import tests.utils as test_utils


class TestUtils(test_utils.BaseTestCase):

    def test__run(self):
        self.patch_object(utils.subprocess, 'check_output')
        self.check_output.return_value = 'aReturn'
        self.assertEquals(utils._run('aArg'), 'aReturn')
        self.check_output.assert_called_once_with(
            ('aArg',), universal_newlines=True)
