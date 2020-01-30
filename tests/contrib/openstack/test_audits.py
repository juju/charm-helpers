from testtools import TestCase, skipIf
from mock import patch, MagicMock, call
import six

import charmhelpers.contrib.openstack.audits as audits
import charmhelpers.contrib.openstack.audits.openstack_security_guide as guide


@skipIf(six.PY2, 'Audits only support Python3')
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

    @patch('charmhelpers.contrib.openstack.audits._audits', {})
    def test_duplicate_audit(self):
        def should_run(audit_options):
            return True

        @audits.audit(should_run)
        def test(options):
            pass

        try:
            # Again!
            #
            # Both of the following '#noqa's are to prevent flake8 from
            # noticing the duplicate function `test`  The intent in this test
            # is for the audits.audit to pick up on the duplicate function.
            @audits.audit(should_run)  # noqa
            def test(options):         # noqa
                pass
        except RuntimeError as e:
            self.assertEqual("Test name 'test' used more than once", e.args[0])
            return
        self.assertTrue(False, "Duplicate audit should raise an exception")

    @patch('charmhelpers.contrib.openstack.audits._audits', {})
    def test_non_callable_filter(self):
        try:
            # Again!
            @audits.audit(3)
            def test(options):
                pass
        except RuntimeError as e:
            self.assertEqual("Configuration includes non-callable filters: [3]", e.args[0])
            return
        self.assertTrue(False, "Duplicate audit should raise an exception")

    @patch('charmhelpers.contrib.openstack.audits._audits', {})
    def test_exclude_config(self):
        variables = {
            'test_run': False,
        }

        @audits.audit()
        def test(options):
            variables['test_run'] = True

        audits.run({'excludes': ['test']})
        self.assertFalse(variables['test_run'])


class AuditsTestCase(TestCase):

    @patch('charmhelpers.contrib.openstack.audits.cmp_pkgrevno')
    def test_since_package_less(self, _cmp_pkgrevno):
        _cmp_pkgrevno.return_value = 1

        verifier = audits.since_package('test', '12.0.0')
        self.assertEqual(verifier(), True)

    @patch('charmhelpers.contrib.openstack.audits.cmp_pkgrevno')
    def test_since_package_greater(self, _cmp_pkgrevno):
        _cmp_pkgrevno.return_value = -1

        verifier = audits.since_package('test', '14.0.0')
        self.assertEqual(verifier(), False)

    @patch('charmhelpers.contrib.openstack.audits.cmp_pkgrevno')
    def test_since_package_equal(self, _cmp_pkgrevno):
        _cmp_pkgrevno.return_value = 0

        verifier = audits.since_package('test', '13.0.0')
        self.assertEqual(verifier(), True)

    @patch('charmhelpers.contrib.openstack.utils.get_os_codename_package')
    def test_since_openstack_less(self, _get_os_codename_package):
        _get_os_codename_package.return_value = "icehouse"

        verifier = audits.since_openstack_release('test', 'mitaka')
        self.assertEqual(verifier(), False)

    @patch('charmhelpers.contrib.openstack.utils.get_os_codename_package')
    def test_since_openstack_greater(self, _get_os_codename_package):
        _get_os_codename_package.return_value = "rocky"

        verifier = audits.since_openstack_release('test', 'queens')
        self.assertEqual(verifier(), True)

    @patch('charmhelpers.contrib.openstack.utils.get_os_codename_package')
    def test_since_openstack_equal(self, _get_os_codename_package):
        _get_os_codename_package.return_value = "mitaka"

        verifier = audits.since_openstack_release('test', 'mitaka')
        self.assertEqual(verifier(), True)

    @patch('charmhelpers.contrib.openstack.utils.get_os_codename_package')
    def test_before_openstack_less(self, _get_os_codename_package):
        _get_os_codename_package.return_value = "icehouse"

        verifier = audits.before_openstack_release('test', 'mitaka')
        self.assertEqual(verifier(), True)

    @patch('charmhelpers.contrib.openstack.utils.get_os_codename_package')
    def test_before_openstack_greater(self, _get_os_codename_package):
        _get_os_codename_package.return_value = "rocky"

        verifier = audits.before_openstack_release('test', 'queens')
        self.assertEqual(verifier(), False)

    @patch('charmhelpers.contrib.openstack.utils.get_os_codename_package')
    def test_before_openstack_equal(self, _get_os_codename_package):
        _get_os_codename_package.return_value = "mitaka"

        verifier = audits.before_openstack_release('test', 'mitaka')
        self.assertEqual(verifier(), False)

    @patch('charmhelpers.contrib.openstack.audits.cmp_pkgrevno')
    def test_before_package_less(self, _cmp_pkgrevno):
        _cmp_pkgrevno.return_value = 1

        verifier = audits.before_package('test', '12.0.0')
        self.assertEqual(verifier(), False)

    @patch('charmhelpers.contrib.openstack.audits.cmp_pkgrevno')
    def test_before_package_greater(self, _cmp_pkgrevno):
        _cmp_pkgrevno.return_value = -1

        verifier = audits.before_package('test', '14.0.0')
        self.assertEqual(verifier(), True)

    @patch('charmhelpers.contrib.openstack.audits.cmp_pkgrevno')
    def test_before_package_equal(self, _cmp_pkgrevno):
        _cmp_pkgrevno.return_value = 0

        verifier = audits.before_package('test', '13.0.0')
        self.assertEqual(verifier(), False)

    def test_is_audit_type_empty(self):
        verifier = audits.is_audit_type(audits.AuditType.OpenStackSecurityGuide)
        self.assertEqual(verifier({}), False)

    def test_is_audit_type(self):
        verifier = audits.is_audit_type(audits.AuditType.OpenStackSecurityGuide)
        self.assertEqual(verifier({'audit_type': audits.AuditType.OpenStackSecurityGuide}), True)


@skipIf(six.PY2, 'Audits only support Python3')
class OpenstackSecurityGuideTestCase(TestCase):

    @patch('configparser.ConfigParser')
    def test_internal_config_parser_is_not_strict(self, _config_parser):
        parser = MagicMock()
        _config_parser.return_value = parser
        guide._config_ini('test')
        _config_parser.assert_called_with(strict=False)
        parser.read.assert_called_with('test')

    @patch('charmhelpers.contrib.openstack.audits.openstack_security_guide._stat')
    def test_internal_validate_file_ownership(self, _stat):
        _stat.return_value = guide.Ownership('test_user', 'test_group', '600')
        guide._validate_file_ownership('test_user', 'test_group', 'test-file-name')
        _stat.assert_called_with('test-file-name')
        pass

    @patch('charmhelpers.contrib.openstack.audits.openstack_security_guide._stat')
    def test_internal_validate_file_mode(self, _stat):
        _stat.return_value = guide.Ownership('test_user', 'test_group', '600')
        guide._validate_file_mode('600', 'test-file-name')
        _stat.assert_called_with('test-file-name')
        pass

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
        _validate_mode.assert_called_once_with('600', 'test', False)

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
        _validate_mode.assert_called_once_with('777', 'test', False)

    @patch('glob.glob')
    @patch('os.path.isfile')
    @patch('charmhelpers.contrib.openstack.audits.openstack_security_guide._validate_file_mode')
    def test_validate_file_permissions_glob(self, _validate_mode, _is_file, _glob):
        _glob.return_value = ['test']
        _is_file.return_value = True
        config = {
            'files': {
                '*': {
                    'mode': '777'
                }
            }
        }
        guide.validate_file_permissions(config)
        _validate_mode.assert_called_once_with('777', 'test', False)

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
        _validate_owner.assert_called_once_with('root', 'root', 'test', False)

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
        _validate_owner.assert_called_once_with('test-user', 'test-group', 'test', False)

    @patch('glob.glob')
    @patch('os.path.isfile')
    @patch('charmhelpers.contrib.openstack.audits.openstack_security_guide._validate_file_ownership')
    def test_validate_file_ownership_glob(self, _validate_owner, _is_file, _glob):
        _glob.return_value = ['test']
        _is_file.return_value = True
        config = {
            'files': {
                '*': {
                    'owner': 'test-user',
                    'group': 'test-group',
                }
            }
        }
        guide.validate_file_ownership(config)
        _validate_owner.assert_called_once_with('test-user', 'test-group', 'test', False)

    @patch('charmhelpers.contrib.openstack.audits.openstack_security_guide._config_section')
    def test_validate_uses_keystone(self, _config_section):
        _config_section.side_effect = [None, {
            'auth_strategy': 'keystone',
        }]
        guide.validate_uses_keystone({})
        _config_section.assert_has_calls([call({}, 'api'), call({}, 'DEFAULT')])

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
