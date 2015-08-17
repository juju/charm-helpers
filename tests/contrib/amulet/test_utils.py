# Copyright 2015 Canonical Ltd.
#
# Authors:
#  Adam Collard <adam.collard@canonical.com>

import unittest

from charmhelpers.contrib.amulet.utils import AmuletUtils


class FakeSentry(object):

    def __init__(self):
        self.commands = {}
        self.info = {"unit_name": "foo"}

    def run(self, command):
        return self.commands[command]


class ValidateServicesByNameTestCase(unittest.TestCase):

    def setUp(self):
        self.utils = AmuletUtils()
        self.sentry_unit = FakeSentry()

    def test_errors_for_unknown_upstart_service(self):
        """
        Returns a message if the Upstart service is unknown.
        """
        self.sentry_unit.commands["lsb_release -cs"] = "trusty", 0
        self.sentry_unit.commands["sudo status foo"] = (
            "status: Unknown job: foo", 1)

        result = self.utils.validate_services_by_name(
            {self.sentry_unit: ["foo"]})
        self.assertIsNotNone(result)

    def test_none_for_started_upstart_service(self):
        """
        Returns None if the Upstart service is running.
        """
        self.sentry_unit.commands["lsb_release -cs"] = "trusty", 0
        self.sentry_unit.commands["sudo status foo"] = (
            "foo start/running, process 42", 0)

        result = self.utils.validate_services_by_name(
            {self.sentry_unit: ["foo"]})
        self.assertIsNone(result)

    def test_errors_for_stopped_upstart_service(self):
        """
        Returns a message if the Upstart service is stopped.
        """
        self.sentry_unit.commands["lsb_release -cs"] = "trusty", 0
        self.sentry_unit.commands["sudo status foo"] = "foo stop/waiting", 0

        result = self.utils.validate_services_by_name(
            {self.sentry_unit: ["foo"]})
        self.assertIsNotNone(result)

    def test_errors_for_unknown_systemd_service(self):
        """
        Returns a message if a systemd service is unknown.
        """
        self.sentry_unit.commands["lsb_release -cs"] = "vivid", 0
        self.sentry_unit.commands["sudo service foo status"] = (u"""\
\u25cf foo.service
   Loaded: not-found (Reason: No such file or directory)
   Active: inactive (dead)
""", 3)

        result = self.utils.validate_services_by_name({
            self.sentry_unit: ["foo"]})
        self.assertIsNotNone(result)

    def test_none_for_started_systemd_service(self):
        """
        Returns None if a systemd service is running.
        """
        self.sentry_unit.commands["lsb_release -cs"] = "vivid", 0
        self.sentry_unit.commands["sudo service foo status"] = (u"""\
\u25cf foo.service - Foo
   Loaded: loaded (/lib/systemd/system/foo.service; enabled)
   Active: active (exited) since Thu 1970-01-01 00:00:00 UTC; 42h 42min ago
 Main PID: 3 (code=exited, status=0/SUCCESS)
   CGroup: /system.slice/foo.service
""", 0)
        result = self.utils.validate_services_by_name(
            {self.sentry_unit: ["foo"]})
        self.assertIsNone(result)

    def test_errors_for_stopped_systemd_service(self):
        """
        Returns a message if a systemd service is stopped.
        """
        self.sentry_unit.commands["lsb_release -cs"] = "vivid", 0
        self.sentry_unit.commands["sudo service foo status"] = (u"""\
\u25cf foo.service - Foo
   Loaded: loaded (/lib/systemd/system/foo.service; disabled)
   Active: inactive (dead)
""", 3)
        result = self.utils.validate_services_by_name(
            {self.sentry_unit: ["foo"]})
        self.assertIsNotNone(result)


class RunActionTestCase(unittest.TestCase):

    def setUp(self):
        self.utils = AmuletUtils()
        self.sentry_unit = FakeSentry()

    def test_request_json_output(self):
        """Juju is called with --format=json, to guarantee output format."""
        output_calls = []

        def fake_check_output(call, **kwargs):
            output_calls.append(call)
            return '{"Action queued with id": "action-id"}'

        self.utils.run_action(
            self.sentry_unit, "foo", _check_output=fake_check_output)
        call, = output_calls
        self.assertIn("--format=json", call)

    def test_returns_action_id(self):
        """JSON output is parsed and returns action_id."""

        def fake_check_output(call, **kwargs):
            return '{"Action queued with id": "action-id"}'

        self.assertEqual("action-id", self.utils.run_action(
            self.sentry_unit, "foo", _check_output=fake_check_output))


class WaitActionTestCase(unittest.TestCase):

    def setUp(self):
        self.utils = AmuletUtils()
        self.sentry_unit = FakeSentry()

    def test_request_json_output(self):
        """Juju is called with --format=json, to guarantee output format."""
        output_calls = []

        def fake_check_output(call, **kwargs):
            output_calls.append(call)
            return '{"status": "completed"}'

        self.utils.wait_on_action(
            "action-id", _check_output=fake_check_output)
        call, = output_calls
        self.assertIn("--format=json", call)

    def test_request_indefinitely(self):
        """Juju  with --wait=0, to block until a result is available."""
        output_calls = []

        def fake_check_output(call, **kwargs):
            output_calls.append(call)
            return '{"status": "completed"}'

        self.utils.wait_on_action(
            "action-id", _check_output=fake_check_output)
        call, = output_calls
        self.assertIn("--wait=0", call)

    def test_returns_true_if_completed(self):
        """JSON output is parsed and returns True if the action completed."""
        def fake_check_output(call, **kwargs):
            return '{"status": "completed"}'

        self.assertTrue(self.utils.wait_on_action(
            "action-id", _check_output=fake_check_output))

    def test_returns_false_if_still_running(self):
        """
        JSON output is parsed and returns False if the action is still running.
        """
        def fake_check_output(call, **kwargs):
            return '{"status": "running"}'

        self.assertFalse(self.utils.wait_on_action(
            "action-id", _check_output=fake_check_output))

    def test_returns_false_if_no_status(self):
        """
        JSON output is parsed and returns False if there is no action status.
        """
        def fake_check_output(call, **kwargs):
            return '{"status": "running"}'

        self.assertFalse(self.utils.wait_on_action(
            "action-id", _check_output=fake_check_output))


class GetProcessIdListTestCase(unittest.TestCase):

    def setUp(self):
        self.utils = AmuletUtils()
        self.sentry_unit = FakeSentry()

    def test_returns_pids(self):
        """
        Normal execution returns a list of pids
        """
        self.sentry_unit.commands["pidof -x foo"] = ("123 124 125", 0)
        result = self.utils.get_process_id_list(self.sentry_unit, "foo")
        self.assertEqual(["123", "124", "125"], result)

    def test_fails_if_no_process_found(self):
        """
        By default, the expectation is that a process is running. Failure
        to find a given process results in an amulet.FAIL being
        raised.
        """
        self.sentry_unit.commands["pidof -x foo"] = ("", 1)
        with self.assertRaises(SystemExit) as cm:
            self.utils.get_process_id_list(self.sentry_unit, "foo")
        the_exception = cm.exception
        self.assertEqual(1, the_exception.code)

    def test_looks_for_scripts(self):
        """
        pidof command uses -x to return a list of pids of scripts
        """
        self.sentry_unit.commands["pidof foo"] = ("", 1)
        self.sentry_unit.commands["pidof -x foo"] = ("123 124 125", 0)
        result = self.utils.get_process_id_list(self.sentry_unit, "foo")
        self.assertEqual(["123", "124", "125"], result)

    def test_expect_no_pid(self):
        """
        By setting expectation that there are no pids running the logic
        about when to fail is reversed.
        """
        self.sentry_unit.commands["pidof -x foo || exit 0 && exit 1"] = ("", 0)
        self.sentry_unit.commands["pidof -x bar || exit 0 && exit 1"] = ("", 1)
        result = self.utils.get_process_id_list(
            self.sentry_unit, "foo", expect_success=False)
        self.assertEqual([], result)
        with self.assertRaises(SystemExit) as cm:
            self.utils.get_process_id_list(
                self.sentry_unit, "bar", expect_success=False)
        the_exception = cm.exception
        self.assertEqual(1, the_exception.code)
