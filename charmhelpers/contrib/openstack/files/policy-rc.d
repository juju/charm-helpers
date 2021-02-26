#!/usr/bin/env python3

import collections
import glob
import os
import logging
import sys
import time
import yaml

logging.basicConfig(filename='/var/log/policy-rc.d.log',
    level=logging.DEBUG, 
    format='%(asctime)s %(message)s')

SystemPolicy = collections.namedtuple(
    'SystemPolicy',
    [
        'policy_requestor_name',
        'policy_requestor_type',
        'service',
        'blocked_actions'])


def policy_config_dir():
    return '/etc/policy-rc.d'


def policy_log_dir():
    return '/var/lib/policy-rc.d'


def read_policy_file(policy_file):
    policies = []
    if os.path.exists(policy_file):
        with open(policy_file, 'r') as f:
            policy = yaml.safe_load(f)
        for service, actions in policy['blocked_actions'].items():
            service = service.replace('.service', '')
            policies.append(SystemPolicy(
                policy_requestor_name=policy['policy_requestor_name'],
                policy_requestor_type=policy['policy_requestor_type'],
                service=service,
                blocked_actions=actions))
    return policies


def get_policies():
    _policy = []
    for f in glob.glob('{}/*.policy'.format(policy_config_dir())):
        _policy.extend(read_policy_file(f))
    return _policy


def log_blocked_action(svc, action, blocking_policies):
    if not os.path.exists(policy_log_dir()):
        os.mkdir(policy_log_dir())
    seconds = round(time.time())
    for policy in blocking_policies:
        log_dir = '{}/{}-{}'.format(
                policy_log_dir(),
                policy.policy_requestor_type,
                policy.policy_requestor_name)
        if not os.path.exists(log_dir):
            os.mkdir(log_dir)
        file_name = '{}/{}.deferred'.format(
                log_dir,
                seconds)
        with open(file_name, 'w') as f:
            data = {
                'time': seconds,
                'service': svc,
                'action': action,
                'policy_requestor_type': policy.policy_requestor_type,
                'policy_requestor_name': policy.policy_requestor_name}
            yaml.dump(data, f)


def get_blocking_policies(svc, cmd):
    svc = svc.replace('.service', '')
    blocking_policies = [
        policy
        for policy in get_policies()
        if policy.service == svc and cmd in policy.blocked_actions]
    return blocking_policies


service = sys.argv[1]
cmd = sys.argv[2]

RC = 0
blocking_policies = get_blocking_policies(service, cmd)
if blocking_policies:
    logging.info('{} of {} blocked by {}'.format(
        cmd,
        service,
        ', '.join(
            ['{} {}'.format(p.policy_requestor_type, p.policy_requestor_name)
             for p in blocking_policies])))
    log_blocked_action(service, cmd, blocking_policies)
    RC = 101
else:
    logging.info("Permitting {} {}".format(service, cmd))

sys.exit(RC)
