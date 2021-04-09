import os
import yaml
import subprocess

from testtools import TestCase
from mock import patch, call, MagicMock

from charmhelpers.contrib.charmsupport import nrpe
from charmhelpers.core import host


class NRPEBaseTestCase(TestCase):
    patches = {
        'config': {'object': nrpe},
        'copy2': {'object': nrpe.shutil},
        'log': {'object': nrpe},
        'getpwnam': {'object': nrpe.pwd},
        'getgrnam': {'object': nrpe.grp},
        'glob': {'object': nrpe.glob},
        'mkdir': {'object': os},
        'chown': {'object': os},
        'chmod': {'object': os},
        'exists': {'object': os.path},
        'listdir': {'object': os},
        'remove': {'object': os},
        'open': {'object': nrpe, 'create': True},
        'isfile': {'object': os.path},
        'isdir': {'object': os.path},
        'call': {'object': subprocess},
        'relation_get': {'object': nrpe},
        'relation_ids': {'object': nrpe},
        'relation_set': {'object': nrpe},
        'relations_of_type': {'object': nrpe},
        'service': {'object': nrpe},
        'init_is_systemd': {'object': host},
    }

    def setUp(self):
        super(NRPEBaseTestCase, self).setUp()
        self.patched = {}
        # Mock the universe.
        for attr, data in self.patches.items():
            create = data.get('create', False)
            patcher = patch.object(data['object'], attr, create=create)
            self.patched[attr] = patcher.start()
            self.addCleanup(patcher.stop)
        env_patcher = patch.dict('os.environ',
                                 {'JUJU_UNIT_NAME': 'testunit',
                                  'CHARM_DIR': '/usr/lib/test_charm_dir'})
        env_patcher.start()
        self.addCleanup(env_patcher.stop)

    def check_call_counts(self, **kwargs):
        for attr, expected in kwargs.items():
            patcher = self.patched[attr]
            self.assertEqual(expected, patcher.call_count, attr)


class NRPETestCase(NRPEBaseTestCase):

    def test_init_gets_config(self):
        self.patched['config'].return_value = {'nagios_context': 'testctx',
                                               'nagios_servicegroups': 'testsgrps'}

        checker = nrpe.NRPE()

        self.assertEqual('testctx', checker.nagios_context)
        self.assertEqual('testsgrps', checker.nagios_servicegroups)
        self.assertEqual('testunit', checker.unit_name)
        self.assertEqual('testctx-testunit', checker.hostname)
        self.check_call_counts(config=1)

    def test_init_hostname(self):
        """Test that the hostname parameter is correctly set"""
        checker = nrpe.NRPE()
        self.assertEqual(checker.hostname,
                         "{}-{}".format(checker.nagios_context,
                                        checker.unit_name))
        hostname = "test.host"
        checker = nrpe.NRPE(hostname=hostname)
        self.assertEqual(checker.hostname, hostname)

    def test_default_servicegroup(self):
        """Test that nagios_servicegroups gets set to the default if omitted"""
        self.patched['config'].return_value = {'nagios_context': 'testctx'}
        checker = nrpe.NRPE()
        self.assertEqual(checker.nagios_servicegroups, 'testctx')

    def test_no_nagios_installed_bails(self):
        self.patched['config'].return_value = {'nagios_context': 'test',
                                               'nagios_servicegroups': ''}
        self.patched['getgrnam'].side_effect = KeyError
        checker = nrpe.NRPE()

        self.assertEqual(None, checker.write())

        expected = 'Nagios user not set up, nrpe checks not updated'
        self.patched['log'].assert_called_with(expected)
        self.check_call_counts(log=2, config=1, getpwnam=1, getgrnam=1)

    def test_write_no_checker(self):
        self.patched['config'].return_value = {'nagios_context': 'test',
                                               'nagios_servicegroups': ''}
        self.patched['exists'].return_value = True
        checker = nrpe.NRPE()

        self.assertEqual(None, checker.write())

        self.check_call_counts(config=1, getpwnam=1, getgrnam=1, exists=1)

    def test_write_restarts_service(self):
        self.patched['config'].return_value = {'nagios_context': 'test',
                                               'nagios_servicegroups': ''}
        self.patched['exists'].return_value = True
        checker = nrpe.NRPE()

        self.assertEqual(None, checker.write())

        self.patched['service'].assert_called_with('restart', 'nagios-nrpe-server')
        self.check_call_counts(config=1, getpwnam=1, getgrnam=1,
                               exists=1, service=1)

    def test_update_nrpe(self):
        self.patched['config'].return_value = {'nagios_context': 'a',
                                               'nagios_servicegroups': ''}
        self.patched['exists'].return_value = True
        self.patched['relation_get'].return_value = {
            'egress-subnets': '10.66.111.24/32',
            'ingress-address': '10.66.111.24',
            'private-address': '10.66.111.24'
        }

        def _rels(rname):
            relations = {
                'local-monitors': 'local-monitors:1',
                'nrpe-external-master': 'nrpe-external-master:2',
            }
            return [relations[rname]]
        self.patched['relation_ids'].side_effect = _rels

        checker = nrpe.NRPE()
        checker.add_check(shortname="myservice",
                          description="Check MyService",
                          check_cmd="check_http http://localhost")

        self.assertEqual(None, checker.write())

        self.assertEqual(2, self.patched['open'].call_count)
        filename = 'check_myservice.cfg'
        expected = [
            ('/etc/nagios/nrpe.d/%s' % filename, 'w'),
            ('/var/lib/nagios/export/service__a-testunit_%s' % filename, 'w'),
        ]
        actual = [x[0] for x in self.patched['open'].call_args_list]
        self.assertEqual(expected, actual)
        outfile = self.patched['open'].return_value.__enter__.return_value
        service_file_contents = """
#---------------------------------------------------
# This file is Juju managed
#---------------------------------------------------
define service {
    use                             active-service
    host_name                       a-testunit
    service_description             a-testunit[myservice] Check MyService
    check_command                   check_nrpe!check_myservice
    servicegroups                   a

}
"""
        expected = [
            '# check myservice\n',
            '# The following header was added automatically by juju\n',
            '# Modifying it will affect nagios monitoring and alerting\n',
            '# servicegroups: a\n',
            'command[check_myservice]=/usr/lib/nagios/plugins/check_http http://localhost\n',
            service_file_contents,
        ]
        actual = [x[0][0] for x in outfile.write.call_args_list]
        self.assertEqual(expected, actual)

        nrpe_monitors = {'myservice':
                         {'command': 'check_myservice',
                          }}
        monitors = yaml.dump(
            {"monitors": {"remote": {"nrpe": nrpe_monitors}}})
        relation_set_calls = [
            call(monitors=monitors, relation_id="local-monitors:1"),
            call(monitors=monitors, relation_id="nrpe-external-master:2"),
        ]
        self.patched['relation_set'].assert_has_calls(relation_set_calls, any_order=True)
        self.check_call_counts(config=1, getpwnam=1, getgrnam=1,
                               exists=4, open=2, listdir=1, relation_get=2,
                               relation_ids=3, relation_set=3)

    def test_max_check_attmpts(self):
        self.patched['config'].return_value = {'nagios_context': 'a',
                                               'nagios_servicegroups': ''}
        self.patched['exists'].return_value = True
        self.patched['relation_get'].return_value = {
            'egress-subnets': '10.66.111.24/32',
            'ingress-address': '10.66.111.24',
            'private-address': '10.66.111.24'
        }

        def _rels(rname):
            relations = {
                'local-monitors': 'local-monitors:1',
                'nrpe-external-master': 'nrpe-external-master:2',
            }
            return [relations[rname]]
        self.patched['relation_ids'].side_effect = _rels

        checker = nrpe.NRPE()
        checker.add_check(shortname="myservice",
                          description="Check MyService",
                          check_cmd="check_http http://localhost",
                          max_check_attempts=8,
                          )

        self.assertEqual(None, checker.write())

        self.assertEqual(2, self.patched['open'].call_count)
        filename = 'check_myservice.cfg'
        expected = [
            ('/etc/nagios/nrpe.d/%s' % filename, 'w'),
            ('/var/lib/nagios/export/service__a-testunit_%s' % filename, 'w'),
        ]
        actual = [x[0] for x in self.patched['open'].call_args_list]
        self.assertEqual(expected, actual)
        outfile = self.patched['open'].return_value.__enter__.return_value
        service_file_contents = """
#---------------------------------------------------
# This file is Juju managed
#---------------------------------------------------
define service {
    use                             active-service
    host_name                       a-testunit
    service_description             a-testunit[myservice] Check MyService
    check_command                   check_nrpe!check_myservice
    servicegroups                   a
    max_check_attempts              8
}
"""
        expected = [
            '# check myservice\n',
            '# The following header was added automatically by juju\n',
            '# Modifying it will affect nagios monitoring and alerting\n',
            '# servicegroups: a\n',
            'command[check_myservice]=/usr/lib/nagios/plugins/check_http http://localhost\n',
            service_file_contents,
        ]
        actual = [x[0][0] for x in outfile.write.call_args_list]
        self.assertEqual(expected, actual)

        nrpe_monitors = {'myservice':
                         {'command': 'check_myservice',
                          'max_check_attempts': 8,
                          }}
        monitors = yaml.dump(
            {"monitors": {"remote": {"nrpe": nrpe_monitors}}})
        relation_set_calls = [
            call(monitors=monitors, relation_id="local-monitors:1"),
            call(monitors=monitors, relation_id="nrpe-external-master:2"),
        ]
        self.patched['relation_set'].assert_has_calls(relation_set_calls, any_order=True)
        self.check_call_counts(config=1, getpwnam=1, getgrnam=1,
                               exists=4, open=2, listdir=1, relation_get=2,
                               relation_ids=3, relation_set=3)


class NRPECheckTestCase(NRPEBaseTestCase):

    def test_invalid_shortname(self):
        cases = [
            'invalid:name',
            '',
        ]
        for shortname in cases:
            self.assertRaises(nrpe.CheckException, nrpe.Check, shortname,
                              'description', '/some/command')

    def test_valid_shortname(self):
        cases = [
            '1_number_is_fine',
            'dots.are.good',
            'dashes-ok',
            'UPPER_case_allowed',
            '5',
            '@valid',
        ]
        for shortname in cases:
            check = nrpe.Check(shortname, 'description', '/some/command')
            self.assertEqual(shortname, check.shortname)

    def test_write_removes_existing_config(self):
        self.patched['listdir'].return_value = [
            'foo', 'bar.cfg', '_check_shortname.cfg']
        check = nrpe.Check('shortname', 'description', '/some/command')

        self.assertEqual(None, check.write('testctx', 'hostname', 'testsgrp'))

        expected = '/var/lib/nagios/export/_check_shortname.cfg'
        self.patched['remove'].assert_called_once_with(expected)
        self.check_call_counts(exists=3, remove=1, open=2, listdir=1)

    def test_check_write_nrpe_exportdir_not_accessible(self):
        self.patched['exists'].return_value = False
        check = nrpe.Check('shortname', 'description', '/some/command')

        self.assertEqual(None, check.write('testctx', 'hostname', 'testsgrps'))
        expected = ('Not writing service config as '
                    '/var/lib/nagios/export is not accessible')
        self.patched['log'].assert_has_calls(
            [call(expected)], any_order=True)
        self.check_call_counts(log=2, open=1)

    def test_locate_cmd_no_args(self):
        self.patched['exists'].return_value = True

        check = nrpe.Check('shortname', 'description', '/bin/ls')

        self.assertEqual('/bin/ls', check.check_cmd)

    def test_locate_cmd_not_found(self):
        self.patched['exists'].return_value = False
        check = nrpe.Check('shortname', 'description', 'check_http -x -y -z')

        self.assertEqual('', check.check_cmd)
        self.assertEqual(2, self.patched['exists'].call_count)
        expected = [
            '/usr/lib/nagios/plugins/check_http',
            '/usr/local/lib/nagios/plugins/check_http',
        ]
        actual = [x[0][0] for x in self.patched['exists'].call_args_list]
        self.assertEqual(expected, actual)
        self.check_call_counts(exists=2, log=1)
        expected = 'Check command not found: check_http'
        self.assertEqual(expected, self.patched['log'].call_args[0][0])

    def test_run(self):
        self.patched['exists'].return_value = True
        command = '/usr/bin/wget foo'
        check = nrpe.Check('shortname', 'description', command)

        self.assertEqual(None, check.run())

        self.check_call_counts(exists=1, call=1)
        self.assertEqual(command, self.patched['call'].call_args[0][0])


class NRPEMiscTestCase(NRPEBaseTestCase):
    def test_get_nagios_hostcontext(self):
        rel_info = {
            'nagios_hostname': 'bob-openstack-dashboard-0',
            'private-address': '10.5.3.103',
            '__unit__': u'dashboard-nrpe/1',
            '__relid__': u'nrpe-external-master:2',
            'nagios_host_context': u'bob',
        }
        self.patched['relations_of_type'].return_value = [rel_info]
        self.assertEqual(nrpe.get_nagios_hostcontext(), 'bob')

    def test_get_nagios_hostname(self):
        rel_info = {
            'nagios_hostname': 'bob-openstack-dashboard-0',
            'private-address': '10.5.3.103',
            '__unit__': u'dashboard-nrpe/1',
            '__relid__': u'nrpe-external-master:2',
            'nagios_host_context': u'bob',
        }
        self.patched['relations_of_type'].return_value = [rel_info]
        self.assertEqual(nrpe.get_nagios_hostname(), 'bob-openstack-dashboard-0')

    def test_get_nagios_unit_name(self):
        rel_info = {
            'nagios_hostname': 'bob-openstack-dashboard-0',
            'private-address': '10.5.3.103',
            '__unit__': u'dashboard-nrpe/1',
            '__relid__': u'nrpe-external-master:2',
            'nagios_host_context': u'bob',
        }
        self.patched['relations_of_type'].return_value = [rel_info]
        self.assertEqual(nrpe.get_nagios_unit_name(), 'bob:testunit')

    def test_get_nagios_unit_name_no_hc(self):
        self.patched['relations_of_type'].return_value = []
        self.assertEqual(nrpe.get_nagios_unit_name(), 'testunit')

    @patch.object(os.path, 'isdir')
    def test_add_init_service_checks(self, mock_isdir):
        def _exists(init_file):
            files = ['/etc/init/apache2.conf',
                     '/usr/lib/nagios/plugins/check_upstart_job',
                     '/etc/init.d/haproxy',
                     '/usr/lib/nagios/plugins/check_status_file.py',
                     '/etc/cron.d/nagios-service-check-haproxy',
                     '/var/lib/nagios/service-check-haproxy.txt',
                     '/usr/lib/nagios/plugins/check_systemd.py'
                     ]
            return init_file in files

        self.patched['exists'].side_effect = _exists

        # Test without systemd and /var/lib/nagios does not exist
        self.patched['init_is_systemd'].return_value = False
        mock_isdir.return_value = False
        bill = nrpe.NRPE()
        services = ['apache2', 'haproxy']
        nrpe.add_init_service_checks(bill, services, 'testunit')
        mock_isdir.assert_called_with('/var/lib/nagios')
        self.patched['call'].assert_not_called()
        expect_cmds = {
            'apache2': '/usr/lib/nagios/plugins/check_upstart_job apache2',
            'haproxy': '/usr/lib/nagios/plugins/check_status_file.py -f '
                       '/var/lib/nagios/service-check-haproxy.txt',
        }
        self.assertEqual(bill.checks[0].shortname, 'apache2')
        self.assertEqual(bill.checks[0].check_cmd, expect_cmds['apache2'])
        self.assertEqual(bill.checks[1].shortname, 'haproxy')
        self.assertEqual(bill.checks[1].check_cmd, expect_cmds['haproxy'])

        # without systemd and /var/lib/nagios does exist
        mock_isdir.return_value = True
        f = MagicMock()
        self.patched['open'].return_value = f
        bill = nrpe.NRPE()
        services = ['apache2', 'haproxy']
        nrpe.add_init_service_checks(bill, services, 'testunit')
        mock_isdir.assert_called_with('/var/lib/nagios')
        self.patched['call'].assert_called_with(
            ['/usr/local/lib/nagios/plugins/check_exit_status.pl', '-e', '-s',
             '/etc/init.d/haproxy', 'status'], stdout=f,
            stderr=subprocess.STDOUT)

        # Test regular services and snap services with systemd
        services = ['apache2', 'haproxy', 'snap.test.test',
                    'ceph-radosgw@hostname']
        self.patched['init_is_systemd'].return_value = True
        nrpe.add_init_service_checks(bill, services, 'testunit')
        expect_cmds = {
            'apache2': '/usr/lib/nagios/plugins/check_systemd.py apache2',
            'haproxy': '/usr/lib/nagios/plugins/check_systemd.py haproxy',
            'snap.test.test': '/usr/lib/nagios/plugins/check_systemd.py snap.test.test',
        }
        self.assertEqual(bill.checks[2].shortname, 'apache2')
        self.assertEqual(bill.checks[2].check_cmd, expect_cmds['apache2'])
        self.assertEqual(bill.checks[3].shortname, 'haproxy')
        self.assertEqual(bill.checks[3].check_cmd, expect_cmds['haproxy'])
        self.assertEqual(bill.checks[4].shortname, 'snap.test.test')
        self.assertEqual(bill.checks[4].check_cmd, expect_cmds['snap.test.test'])

    def test_copy_nrpe_checks(self):
        file_presence = {
            'filea': True,
            'fileb': False}
        self.patched['exists'].return_value = True
        self.patched['glob'].return_value = ['filea', 'fileb']
        self.patched['isdir'].side_effect = [False, True]
        self.patched['isfile'].side_effect = lambda x: file_presence[x]
        nrpe.copy_nrpe_checks()
        self.patched['glob'].assert_called_once_with(
            ('/usr/lib/test_charm_dir/hooks/charmhelpers/contrib/openstack/'
             'files/check_*'))
        self.patched['copy2'].assert_called_once_with(
            'filea',
            '/usr/local/lib/nagios/plugins/filea')

    def test_copy_nrpe_checks_other_root(self):
        file_presence = {
            'filea': True,
            'fileb': False}
        self.patched['exists'].return_value = True
        self.patched['glob'].return_value = ['filea', 'fileb']
        self.patched['isdir'].side_effect = [True, False]
        self.patched['isfile'].side_effect = lambda x: file_presence[x]
        nrpe.copy_nrpe_checks()
        self.patched['glob'].assert_called_once_with(
            ('/usr/lib/test_charm_dir/charmhelpers/contrib/openstack/'
             'files/check_*'))
        self.patched['copy2'].assert_called_once_with(
            'filea',
            '/usr/local/lib/nagios/plugins/filea')

    def test_copy_nrpe_checks_nrpe_files_dir(self):
        file_presence = {
            'filea': True,
            'fileb': False}
        self.patched['exists'].return_value = True
        self.patched['glob'].return_value = ['filea', 'fileb']
        self.patched['isfile'].side_effect = lambda x: file_presence[x]
        nrpe.copy_nrpe_checks(nrpe_files_dir='/other/dir')
        self.patched['glob'].assert_called_once_with(
            '/other/dir/check_*')
        self.patched['copy2'].assert_called_once_with(
            'filea',
            '/usr/local/lib/nagios/plugins/filea')
