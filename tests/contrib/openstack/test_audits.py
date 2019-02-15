from testtools import TestCase
from mock import patch

import charmhelpers.contrib.openstack.audits as audits
import charmhelpers.contrib.openstack.audits.openstack_security_guide as guide


class AuditTestCase(TestCase):

    @patch('charmhelpers.contrib.openstack.audits._audits', {})
    def test_wrapper(self):
        variables = {
            'guard_called': False,
            'test_run': False,
        }

        def should_run(audit_options):
            variables['guard_called'] = True
            return True

        @audits.audit(should_run)
        def test(options):
            variables['test_run'] = True

        audits.run({})
        self.assertTrue(variables['guard_called'])
        self.assertTrue(variables['test_run'])
        self.assertEqual(audits._audits['test'], audits.Audit(test, (should_run,)))

    @patch('charmhelpers.contrib.openstack.audits._audits', {})
    def test_wrapper_not_run(self):
        variables = {
            'guard_called': False,
            'test_run': False,
        }

        def should_run(audit_options):
            variables['guard_called'] = True
            return False

        @audits.audit(should_run)
        def test(options):
            variables['test_run'] = True

        audits.run({})
        self.assertTrue(variables['guard_called'])
        self.assertFalse(variables['test_run'])
        self.assertEqual(audits._audits['test'], audits.Audit(test, (should_run,)))


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


class OpenstackSecurityGuideTestcase(TestCase):

    @patch('os.path.isfile')
    @patch('charmhelpers.contrib.openstack.audits.openstack_security_guide._validate_file_mode')
    def test_validate_file_permissions_defaults(self, _validate_mode, _is_file):
        _is_file.return_value = True
        config = {
            'files': {
                'test': {}
            }
        }
        guide.validate_file_permissions(config)
        _validate_mode.assert_called_once_with('600', 'test')

    @patch('os.path.isfile')
    @patch('charmhelpers.contrib.openstack.audits.openstack_security_guide._validate_file_mode')
    def test_validate_file_permissions(self, _validate_mode, _is_file):
        _is_file.return_value = True
        config = {
            'files': {
                'test': {
                    'mode': '777'
                }
            }
        }
        guide.validate_file_permissions(config)
        _validate_mode.assert_called_once_with('777', 'test')

    @patch('os.path.isfile')
    @patch('charmhelpers.contrib.openstack.audits.openstack_security_guide._validate_file_ownership')
    def test_validate_file_ownership_defaults(self, _validate_owner, _is_file):
        _is_file.return_value = True
        config = {
            'files': {
                'test': {}
            }
        }
        guide.validate_file_ownership(config)
        _validate_owner.assert_called_once_with('root', 'root', 'test')

    @patch('os.path.isfile')
    @patch('charmhelpers.contrib.openstack.audits.openstack_security_guide._validate_file_ownership')
    def test_validate_file_ownership(self, _validate_owner, _is_file):
        _is_file.return_value = True
        config = {
            'files': {
                'test': {
                    'owner': 'test-user',
                    'group': 'test-group',
                }
            }
        }
        guide.validate_file_ownership(config)
        _validate_owner.assert_called_once_with('test-user', 'test-group', 'test')

    @patch('charmhelpers.contrib.openstack.audits.openstack_security_guide._config_section')
    def test_validate_uses_keystone(self, _config_section):
        _config_section.return_value = {
            'auth_strategy': 'keystone',
        }
        guide.validate_uses_keystone({})
        _config_section.assert_called_with({}, 'DEFAULT')

    @patch('charmhelpers.contrib.openstack.audits.openstack_security_guide._config_section')
    def test_validate_uses_tls_for_keystone(self, _config_section):
        _config_section.return_value = {
            'auth_uri': 'https://10.10.10.10',
        }
        guide.validate_uses_tls_for_keystone({})
        _config_section.assert_called_with({}, 'keystone_authtoken')

    @patch('charmhelpers.contrib.openstack.audits.openstack_security_guide._config_section')
    def test_validate_uses_tls_for_glance(self, _config_section):
        _config_section.return_value = {
            'api_servers': 'https://10.10.10.10',
        }
        guide.validate_uses_tls_for_glance({})
        _config_section.assert_called_with({}, 'glance')
