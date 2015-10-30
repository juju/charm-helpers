import os
import yaml
import subprocess

from testtools import TestCase
from mock import patch, call

from charmhelpers.contrib.charmsupport import nrpe


class NRPEBaseTestCase(TestCase):
    patches = {
        'config': {'object': nrpe},
        'log': {'object': nrpe},
        'getpwnam': {'object': nrpe.pwd},
        'getgrnam': {'object': nrpe.grp},
        'mkdir': {'object': os},
        'chown': {'object': os},
        'exists': {'object': os.path},
        'listdir': {'object': os},
        'remove': {'object': os},
        'open': {'object': nrpe, 'create': True},
        'isfile': {'object': os.path},
        'call': {'object': subprocess},
        'relation_ids': {'object': nrpe},
        'relation_set': {'object': nrpe},
        'relations_of_type': {'object': nrpe},
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
        self.patched['log'].assert_called_once_with(expected)
        self.check_call_counts(log=1, config=1, getpwnam=1, getgrnam=1)

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

        expected = ['service', 'nagios-nrpe-server', 'restart']
        self.assertEqual(expected, self.patched['call'].call_args[0][0])
        self.check_call_counts(config=1, getpwnam=1, getgrnam=1,
                               exists=1, call=1)

    def test_update_nrpe(self):
        self.patched['config'].return_value = {'nagios_context': 'a',
                                               'nagios_servicegroups': ''}
        self.patched['exists'].return_value = True

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
            'command[check_myservice]=/usr/lib/nagios/plugins/check_http http://localhost\n',
            service_file_contents,
        ]
        actual = [x[0][0] for x in outfile.write.call_args_list]
        self.assertEqual(expected, actual)

        nrpe_monitors = {'myservice':
                         {'command': 'check_myservice'}}
        monitors = yaml.dump(
            {"monitors": {"remote": {"nrpe": nrpe_monitors}}})
        relation_set_calls = [
            call(monitors=monitors, relation_id="local-monitors:1"),
            call(monitors=monitors, relation_id="nrpe-external-master:2"),
        ]
        self.patched['relation_set'].assert_has_calls(relation_set_calls, any_order=True)
        self.check_call_counts(config=1, getpwnam=1, getgrnam=1,
                               exists=4, open=2, listdir=1,
                               relation_ids=2, relation_set=2)


class NRPECheckTestCase(NRPEBaseTestCase):

    def test_invalid_shortname(self):
        cases = [
            'invalid:name',
            '@invalid',
            '',
        ]
        for shortname in cases:
            self.assertRaises(nrpe.CheckException, nrpe.Check, shortname,
                              'description', '/some/command')

    def test_valid_shortname(self):
        cases = [
            '1_number_is_fine',
            'dashes-ok',
            '5',
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

    def test_add_init_service_checks(self):
        def _exists(init_file):
            files = ['/etc/init/apache2.conf',
                     '/usr/lib/nagios/plugins/check_upstart_job',
                     '/etc/init.d/haproxy',
                     '/usr/lib/nagios/plugins/check_status_file.py',
                     ]
            return init_file in files

        self.patched['exists'].side_effect = _exists
        bill = nrpe.NRPE()
        services = ['apache2', 'haproxy']
        nrpe.add_init_service_checks(bill, services, 'testunit')
        expect_cmds = {
            'apache2': '/usr/lib/nagios/plugins/check_upstart_job apache2',
            'haproxy': '/usr/lib/nagios/plugins/check_status_file.py -f '
                       '/var/lib/nagios/service-check-haproxy.txt',
        }
        self.assertEqual(bill.checks[0].shortname, 'apache2')
        self.assertEqual(bill.checks[0].check_cmd, expect_cmds['apache2'])
        self.assertEqual(bill.checks[1].shortname, 'haproxy')
        self.assertEqual(bill.checks[1].check_cmd, expect_cmds['haproxy'])
