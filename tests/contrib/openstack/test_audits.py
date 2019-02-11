from testtools import TestCase
from mock import patch

import charmhelpers.contrib.openstack.audits as audits


class AuditsTestCase(TestCase):

    @patch('charmhelpers.contrib.openstack.audits.get_upstream_version')
    def test_since_package_less(self, _get_upstream_version):
        _get_upstream_version.return_value = '13.0.0'

        verifier = audits.since_package('test', '12.0.0')
        self.assertEqual(verifier(), True)

    @patch('charmhelpers.contrib.openstack.audits.get_upstream_version')
    def test_since_package_greater(self, _get_upstream_version):
        _get_upstream_version.return_value = '13.0.0'

        verifier = audits.since_package('test', '14.0.0')
        self.assertEqual(verifier(), False)

    @patch('charmhelpers.contrib.openstack.audits.get_upstream_version')
    def test_since_package_equal(self, _get_upstream_version):
        _get_upstream_version.return_value = '13.0.0'

        verifier = audits.since_package('test', '13.0.0')
        self.assertEqual(verifier(), True)

    @patch('charmhelpers.contrib.openstack.audits.get_upstream_version')
    def test_before_package_less(self, _get_upstream_version):
        _get_upstream_version.return_value = '13.0.0'

        verifier = audits.before_package('test', '12.0.0')
        self.assertEqual(verifier(), False)

    @patch('charmhelpers.contrib.openstack.audits.get_upstream_version')
    def test_before_package_greater(self, _get_upstream_version):
        _get_upstream_version.return_value = '13.0.0'

        verifier = audits.before_package('test', '14.0.0')
        self.assertEqual(verifier(), True)

    @patch('charmhelpers.contrib.openstack.audits.get_upstream_version')
    def test_before_package_equal(self, _get_upstream_version):
        _get_upstream_version.return_value = '13.0.0'

        verifier = audits.before_package('test', '13.0.0')
        self.assertEqual(verifier(), False)
