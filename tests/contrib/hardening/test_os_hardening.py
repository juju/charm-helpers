import six

from mock import patch
from testtools import TestCase

CONFIG = {'harden': False}


with patch('charmhelpers.core.hookenv.config', lambda key: CONFIG.get('key')):
    from charmhelpers.contrib.hardening.os_hardening import harden

from charmhelpers.contrib.hardening.templating import HardeningConfigRenderer


class OSHardeningTestCase(TestCase):

    def setUp(self):
        super(OSHardeningTestCase, self).setUp()

    @patch.object(harden.templating.HardeningConfigRenderer, 'render')
    def test_register_configs(self, mock_render):
        configs = harden.register_configs()
        self.assertEquals(type(configs), HardeningConfigRenderer)
        self.assertFalse(mock_render.called)

    @patch.object(harden, 'apt_purge')
    @patch.object(harden, 'apt_install')
    def test_configs_render(self, mock_apt_install, mock_apt_purge):
        configs = harden.register_configs()
        [configs.render(k) for k in six.iterkeys(configs.templates)]
