from mock import patch
from testtools import TestCase

# Ensure no unexpected writes
with patch('charmhelpers.contrib.hardening.templating.'
           'HardeningConfigRenderer'):
    from charmhelpers.contrib.hardening.os_hardening import harden


class OSHardeningTestCase(TestCase):

    def setUp(self):
        super(OSHardeningTestCase, self).setUp()

    def test_register_os_configs(self):
        harden.register_os_configs()
