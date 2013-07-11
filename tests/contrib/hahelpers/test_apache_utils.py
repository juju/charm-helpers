from mock import patch

from testtools import TestCase

import charmhelpers.contrib.hahelpers.apache as apache_utils


class ApacheUtilsTests(TestCase):
    def setUp(self):
        super(ApacheUtilsTests, self).setUp()
        [self._patch(m) for m in [
            'log',
            'config_get',
            'relation_get',
            'relation_ids',
            'relation_list',
        ]]

    def _patch(self, method):
        _m = patch.object(apache_utils, method)
        mock = _m.start()
        self.addCleanup(_m.stop)
        setattr(self, method, mock)

    def test_get_cert_from_config(self):
        '''Ensure cert and key from charm config override relation'''
        self.config_get.side_effect = [
            'some_ca_cert',  # config_get('ssl_cert')
            'some_ca_key',  # config_Get('ssl_key')
        ]
        result = apache_utils.get_cert()
        self.assertEquals(('some_ca_cert', 'some_ca_key'), result)

    def test_get_cert_from_Relation(self):
        self.config_get.return_value = None
        self.relation_ids.return_value = 'identity-service:0'
        self.relation_list.return_value = 'keystone/0'
        self.relation_get.side_effect = [
            'keystone_provided_cert',
            'keystone_provided_key',
        ]
        result = apache_utils.get_cert()
        self.assertEquals(('keystone_provided_cert', 'keystone_provided_key'),
                          result)
