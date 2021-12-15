#!/usr/bin/python3
"""
Checks for services with deferred service restarts.

This Nagios check will parse /var/lib/policy-rd.d/
to find any restarts that are currently deferred.
"""

import argparse
import glob
import sys
import yaml


DEFERRED_EVENTS_DIR = '/var/lib/policy-rc.d'


def get_deferred_events():
    """
    Return a list of deferred events dicts from policy-rc.d files

    Events are of the form:
     {
        action: restart,
        policy_requestor_name: rabbitmq-server,
        policy_requestor_type: charm,
        reason: 'Pkg update',
        service: rabbitmq-server,
        time: 1614328743
    }

    :returns: List of deferred event dicts
    :rtype: List
    """
    deferred_events_files = glob.glob(
        '{}/*.deferred'.format(DEFERRED_EVENTS_DIR))

    deferred_events = []
    for event_file in deferred_events_files:
        with open(event_file, 'r') as f:
            event = yaml.safe_load(f)
            deferred_events.append(event)

    return deferred_events


def get_deferred_restart_services(application=None):
    """
    Reads deferred events and returns a list of services with deferred restarts.

    :param str application: Name of the application that blocked the service restart.
                            If application is None, all services with deferred restarts
                            are returned. Services which are blocked by a non-charm
                            requestor are always returned.
    :returns: List of services with deferred restarts belonging to application.
    :rtype: List[str]
    """

    deferred_restart_events = filter(
        lambda e: e['action'] == 'restart', get_deferred_events())

    deferred_restart_services = set()
    for restart_event in deferred_restart_events:
        if application:
            if (
                restart_event['policy_requestor_type'] != 'charm' or
                restart_event['policy_requestor_type'] == 'charm' and
                restart_event['policy_requestor_name'] == application
            ):
                deferred_restart_services.add(restart_event['service'])
        else:
            deferred_restart_services.add(restart_event['service'])

    return list(deferred_restart_services)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Check for services with deferred restarts')
    parser.add_argument(
        '--application', help='Check services belonging to this application only')

    args = parser.parse_args()

    services = set(get_deferred_restart_services(args.application))

    if not len(services):
        print('OK: No deferred service restarts.')
        sys.exit(0)
    else:
        print(
            'CRITICAL: Restarts are deferred for services: {}.'.format(', '.join(services)))
        sys.exit(2)
