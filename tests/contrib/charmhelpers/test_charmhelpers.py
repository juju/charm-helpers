# Tests for Python charm helpers.

import unittest
import yaml
from testtools import TestCase

from io import StringIO

import sys
# Path hack to ensure we test the local code, not a version installed in
# /usr/local/lib.  This is necessary since /usr/local/lib is prepended before
# what is specified in PYTHONPATH.
sys.path.insert(0, 'helpers/python')
from charmhelpers.contrib import charmhelpers  # noqa


class CharmHelpersTestCase(TestCase):
    """A basic test case for Python charm helpers."""

    def _patch_command(self, replacement_command):
        """Monkeypatch charmhelpers.command for testing purposes.

        :param replacement_command: The replacement Callable for
                                    command().
        """
        self.patch(charmhelpers, 'command', lambda *args: replacement_command)

    def _make_juju_status_dict(self, num_units=1,
                               service_name='test-service',
                               unit_state='pending',
                               machine_state='not-started'):
        """Generate valid juju status dict and return it."""
        machine_data = {}
        # The 0th machine is the Zookeeper.
        machine_data[0] = {'dns-name': 'zookeeper.example.com',
                           'instance-id': 'machine0',
                           'state': 'not-started'}
        service_data = {'charm': 'local:precise/{}-1'.format(service_name),
                        'relations': {},
                        'units': {}}
        for i in range(num_units):
            # The machine is always going to be i+1 because there
            # will always be num_units+1 machines.
            machine_number = i + 1
            unit_machine_data = {
                'dns-name': 'machine{}.example.com'.format(machine_number),
                'instance-id': 'machine{}'.format(machine_number),
                'state': machine_state,
                'instance-state': machine_state}
            machine_data[machine_number] = unit_machine_data
            unit_data = {
                'machine': machine_number,
                'public-address':
                '{}-{}.example.com'.format(service_name, i),
                'relations': {'db': {'state': 'up'}},
                'agent-state': unit_state}
            service_data['units']['{}/{}'.format(service_name, i)] = (
                unit_data)
        juju_status_data = {'machines': machine_data,
                            'services': {service_name: service_data}}
        return juju_status_data

    def _make_juju_status_yaml(self, num_units=1,
                               service_name='test-service',
                               unit_state='pending',
                               machine_state='not-started'):
        """Convert the dict returned by `_make_juju_status_dict` to YAML."""
        return yaml.dump(
            self._make_juju_status_dict(
                num_units, service_name, unit_state, machine_state))

    def test_make_charm_config_file(self):
        # make_charm_config_file() writes the passed configuration to a
        # temporary file as YAML.
        charm_config = {'foo': 'bar',
                        'spam': 'eggs',
                        'ham': 'jam'}
        # make_charm_config_file() returns the file object so that it
        # can be garbage collected properly.
        charm_config_file = charmhelpers.make_charm_config_file(charm_config)
        with open(charm_config_file.name) as config_in:
            written_config = config_in.read()
        self.assertEqual(yaml.dump(charm_config), written_config)

    def test_unit_info(self):
        # unit_info returns requested data about a given service.
        juju_yaml = self._make_juju_status_yaml()
        self.patch(charmhelpers, 'juju_status', lambda: juju_yaml)
        self.assertEqual(
            'pending',
            charmhelpers.unit_info('test-service', 'agent-state'))

    def test_unit_info_returns_empty_for_nonexistent_service(self):
        # If the service passed to unit_info() has not yet started (or
        # otherwise doesn't exist), unit_info() will return an empty
        # string.
        juju_yaml = "services: {}"
        self.patch(charmhelpers, 'juju_status', lambda: juju_yaml)
        self.assertEqual(
            '', charmhelpers.unit_info('test-service', 'state'))

    def test_unit_info_accepts_data(self):
        # It's possible to pass a `data` dict, containing the parsed
        # result of juju status, to unit_info().
        juju_status_data = yaml.safe_load(
            self._make_juju_status_yaml())
        self.patch(charmhelpers, 'juju_status', lambda: None)
        service_data = juju_status_data['services']['test-service']
        unit_info_dict = service_data['units']['test-service/0']
        for key, value in unit_info_dict.items():
            item_info = charmhelpers.unit_info(
                'test-service', key, data=juju_status_data)
            self.assertEqual(value, item_info)

    def test_unit_info_returns_first_unit_by_default(self):
        # By default, unit_info() just returns the value of the
        # requested item for the first unit in a service.
        juju_yaml = self._make_juju_status_yaml(num_units=2)
        self.patch(charmhelpers, 'juju_status', lambda: juju_yaml)
        unit_address = charmhelpers.unit_info(
            'test-service', 'public-address')
        self.assertEqual('test-service-0.example.com', unit_address)

    def test_unit_info_accepts_unit_name(self):
        # By default, unit_info() just returns the value of the
        # requested item for the first unit in a service. However, it's
        # possible to pass a unit name to it, too.
        juju_yaml = self._make_juju_status_yaml(num_units=2)
        self.patch(charmhelpers, 'juju_status', lambda: juju_yaml)
        unit_address = charmhelpers.unit_info(
            'test-service', 'public-address', unit='test-service/1')
        self.assertEqual('test-service-1.example.com', unit_address)

    def test_get_machine_data(self):
        # get_machine_data() returns a dict containing the machine data
        # parsed from juju status.
        juju_yaml = self._make_juju_status_yaml()
        self.patch(charmhelpers, 'juju_status', lambda: juju_yaml)
        machine_0_data = charmhelpers.get_machine_data()[0]
        self.assertEqual('zookeeper.example.com', machine_0_data['dns-name'])

    def test_wait_for_machine_returns_if_machine_up(self):
        # If wait_for_machine() is called and the machine(s) it is
        # waiting for are already up, it will return.
        juju_yaml = self._make_juju_status_yaml(machine_state='running')
        self.patch(charmhelpers, 'juju_status', lambda: juju_yaml)
        machines, time_taken = charmhelpers.wait_for_machine(timeout=1)
        self.assertEqual(1, machines)

    def test_wait_for_machine_times_out(self):
        # If the machine that wait_for_machine is waiting for isn't
        # 'running' before the passed timeout is reached,
        # wait_for_machine will raise an error.
        juju_yaml = self._make_juju_status_yaml()
        self.patch(charmhelpers, 'juju_status', lambda: juju_yaml)
        self.assertRaises(
            RuntimeError, charmhelpers.wait_for_machine, timeout=0)

    def test_wait_for_machine_always_returns_if_running_locally(self):
        # If juju is actually running against a local LXC container,
        # wait_for_machine will always return.
        juju_status_dict = self._make_juju_status_dict()
        # We'll update the 0th machine to make it look like it's an LXC
        # container.
        juju_status_dict['machines'][0]['dns-name'] = 'localhost'
        juju_yaml = yaml.dump(juju_status_dict)
        self.patch(charmhelpers, 'juju_status', lambda: juju_yaml)
        machines, time_taken = charmhelpers.wait_for_machine(timeout=1)
        # wait_for_machine will always return 1 machine started here,
        # since there's only one machine to start.
        self.assertEqual(1, machines)
        # time_taken will be 0, since no actual waiting happened.
        self.assertEqual(0, time_taken)

    def test_wait_for_machine_waits_for_multiple_machines(self):
        # wait_for_machine can be told to wait for multiple machines.
        juju_yaml = self._make_juju_status_yaml(
            num_units=2, machine_state='running')
        self.patch(charmhelpers, 'juju_status', lambda: juju_yaml)
        machines, time_taken = charmhelpers.wait_for_machine(num_machines=2)
        self.assertEqual(2, machines)

    def test_wait_for_unit_returns_if_unit_started(self):
        # wait_for_unit() will return if the service it's waiting for is
        # already up.
        juju_yaml = self._make_juju_status_yaml(
            unit_state='started', machine_state='running')
        self.patch(charmhelpers, 'juju_status', lambda: juju_yaml)
        charmhelpers.wait_for_unit('test-service', timeout=0)

    def test_wait_for_unit_raises_error_on_error_state(self):
        # If the unit is in some kind of error state, wait_for_unit will
        # raise a RuntimeError.
        juju_yaml = self._make_juju_status_yaml(
            unit_state='start-error', machine_state='running')
        self.patch(charmhelpers, 'juju_status', lambda: juju_yaml)
        self.assertRaises(RuntimeError, charmhelpers.wait_for_unit,
                          'test-service', timeout=0)

    def test_wait_for_unit_raises_error_on_timeout(self):
        # If the unit does not start before the timeout is reached,
        # wait_for_unit will raise a RuntimeError.
        juju_yaml = self._make_juju_status_yaml(
            unit_state='pending', machine_state='running')
        self.patch(charmhelpers, 'juju_status', lambda: juju_yaml)
        self.assertRaises(RuntimeError, charmhelpers.wait_for_unit,
                          'test-service', timeout=0)

    def test_wait_for_relation_returns_if_relation_up(self):
        # wait_for_relation() waits for relations to come up. If a
        # relation is already 'up', wait_for_relation() will return
        # immediately.
        juju_yaml = self._make_juju_status_yaml(
            unit_state='started', machine_state='running')
        self.patch(charmhelpers, 'juju_status', lambda: juju_yaml)
        charmhelpers.wait_for_relation('test-service', 'db', timeout=0)

    def test_wait_for_relation_times_out_if_relation_not_present(self):
        # If a relation does not exist at all before a timeout is
        # reached, wait_for_relation() will raise a RuntimeError.
        juju_dict = self._make_juju_status_dict(
            unit_state='started', machine_state='running')
        units = juju_dict['services']['test-service']['units']
        # We'll remove all the relations for test-service for this test.
        units['test-service/0']['relations'] = {}
        juju_dict['services']['test-service']['units'] = units
        juju_yaml = yaml.dump(juju_dict)
        self.patch(charmhelpers, 'juju_status', lambda: juju_yaml)
        self.assertRaises(
            RuntimeError, charmhelpers.wait_for_relation, 'test-service',
            'db', timeout=0)

    def test_wait_for_relation_times_out_if_relation_not_up(self):
        # If a relation does not transition to an 'up' state, before a
        # timeout is reached, wait_for_relation() will raise a
        # RuntimeError.
        juju_dict = self._make_juju_status_dict(
            unit_state='started', machine_state='running')
        units = juju_dict['services']['test-service']['units']
        units['test-service/0']['relations']['db']['state'] = 'down'
        juju_dict['services']['test-service']['units'] = units
        juju_yaml = yaml.dump(juju_dict)
        self.patch(charmhelpers, 'juju_status', lambda: juju_yaml)
        self.assertRaises(
            RuntimeError, charmhelpers.wait_for_relation, 'test-service',
            'db', timeout=0)

    def test_wait_for_page_contents_returns_if_contents_available(self):
        # wait_for_page_contents() will wait until a given string is
        # contained within the results of a given url and will return
        # once it does.
        # We need to patch the charmhelpers instance of urlopen so that
        # it doesn't try to connect out.
        test_content = "Hello, world."
        self.patch(charmhelpers, 'urlopen',
                   lambda *args: StringIO(test_content))
        charmhelpers.wait_for_page_contents(
            'http://example.com', test_content, timeout=0)

    def test_wait_for_page_contents_times_out(self):
        # If the desired contents do not appear within the page before
        # the specified timeout, wait_for_page_contents() will raise a
        # RuntimeError.
        # We need to patch the charmhelpers instance of urlopen so that
        # it doesn't try to connect out.
        self.patch(charmhelpers, 'urlopen',
                   lambda *args: StringIO("This won't work."))
        self.assertRaises(
            RuntimeError, charmhelpers.wait_for_page_contents,
            'http://example.com', "This will error", timeout=0)


if __name__ == '__main__':
    unittest.main()
