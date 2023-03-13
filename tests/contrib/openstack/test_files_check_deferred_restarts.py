from mock import patch

import charmhelpers.contrib.openstack.files.check_deferred_restarts as check_deferred_restarts
from charmhelpers.contrib.openstack.files.check_deferred_restarts import get_deferred_restart_services
import tests.utils


class CheckDeferredRestartsTestCase(tests.utils.BaseTestCase):

    @patch.object(check_deferred_restarts, "get_deferred_events")
    def test_get_deferred_restart_services_no_restarts(self, mock_get_deferred_events):
        mock_get_deferred_events.return_value = [
            {
                "action": "other_action",
                "service": "service1",
            }
        ]

        services = get_deferred_restart_services()
        self.assertListEqual(services, [])

    @patch.object(check_deferred_restarts, "get_deferred_events")
    def test_get_deferred_restart_services_same_application(self, mock_get_deferred_events):
        mock_get_deferred_events.return_value = [
            {
                "action": "restart",
                "service": "service1",
                "policy_requestor_type": "charm",
                "policy_requestor_name": "app1",
            }, {
                "action": "restart",
                "service": "service2",
                "policy_requestor_type": "charm",
                "policy_requestor_name": "app1",
            }
        ]

        services = get_deferred_restart_services()
        self.assertSetEqual(set(services), set(["service1", "service2"]))

        services = get_deferred_restart_services("app1")
        self.assertSetEqual(set(services), set(["service1", "service2"]))

    @patch.object(check_deferred_restarts, "get_deferred_events")
    def test_get_deferred_restart_services_different_applications(self, mock_get_deferred_events):
        mock_get_deferred_events.return_value = [
            {
                "action": "restart",
                "service": "service1",
                "policy_requestor_type": "charm",
                "policy_requestor_name": "app1",
            }, {
                "action": "restart",
                "service": "service2",
                "policy_requestor_type": "charm",
                "policy_requestor_name": "app2",
            }
        ]

        services = get_deferred_restart_services()
        self.assertSetEqual(set(services), set(["service1", "service2"]))

        services = get_deferred_restart_services("app1")
        self.assertSetEqual(set(services), set(["service1"]))

    @patch.object(check_deferred_restarts, "get_deferred_events")
    def test_get_deferred_restart_services_other_requestor(self, mock_get_deferred_events):
        mock_get_deferred_events.return_value = [
            {
                "action": "restart",
                "service": "service1",
                "policy_requestor_type": "charm",
                "policy_requestor_name": "app1",
            }, {
                "action": "restart",
                "service": "service2",
                "policy_requestor_type": "not_charm",
                "policy_requestor_name": "app2",
            }
        ]

        services = get_deferred_restart_services()
        self.assertSetEqual(set(services), set(["service1", "service2"]))

        services = get_deferred_restart_services("app1")
        self.assertSetEqual(set(services), set(["service1", "service2"]))
