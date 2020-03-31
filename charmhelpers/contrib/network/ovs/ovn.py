# Copyright 2019 Canonical Ltd
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import os
import subprocess

from . import utils


OVN_RUNDIR = '/var/run/ovn'
OVN_SYSCONFDIR = '/etc/ovn'


# TODO: Make use of the new `ovn-appctl` if/when that makes sense
def ovs_appctl(target, args, rundir=None):
    """Run `ovs-appctl` for target with args and return output.

    :param target: Name of daemon to contact.  Unless target begins with '/',
                   `ovs-appctl` looks for a pidfile and will build the path to
                   a /var/run/openvswitch/target.pid.ctl for you.
    :type target: str
    :param args: Command and arguments to pass to `ovs-appctl`
    :type args: Tuple[str, ...]
    :param rundir: Override path to sockets
    :type rundir: Optional[str]
    :returns: Output from command
    :rtype: str
    :raises: subprocess.CalledProcessError
    """
    # NOTE(fnordahl): The ovsdb-server processes for the OVN databases use a
    # non-standard naming scheme for their daemon control socket and we need
    # to pass the full path to the socket.
    if target in ('ovnnb_db', 'ovnsb_db',):
        target = os.path.join(rundir or OVN_RUNDIR, target + '.ctl')
    return utils._run('ovs-appctl', '-t', target, *args)


def cluster_status(target, schema=None):
    """Retrieve status information from clustered OVSDB.

    :param target: Usually one of 'ovsdb-server', 'ovnnb_db', 'ovnsb_db', can
                   also be full path to control socket.
    :type target: str
    :param schema: Database schema name, deduced from target if not provided
    :type schema: Optional[str]
    :returns: Structured cluster status data
    :rtype: Dict[str, Union[str, List[str], Tuple[str, str]]]
    :raises: subprocess.CalledProcessError
    """
    schema_map = {
        'ovnnb_db': 'OVN_Northbound',
        'ovnsb_db': 'OVN_Southbound',
    }
    status = {}
    k = ''
    for line in ovs_appctl(
            target,
            'cluster/status',
            schema or schema_map.get(target)).splitlines():
        if k and line.startswith(' '):
            # there is no key which means this is a instance of a multi-line/
            # multi-value item, populate the List which is already stored under
            # the key.
            status[k].append(line.lstrip())
        elif ':' in line:
            # this is a line with a key
            k, v = line.split(':', 1)
            k = k.lower()
            k = k.replace(' ', '_')
            if v:
                # this is a line with both key and value
                if k in ('cluster_id', 'server_id',):
                    v = v.replace('(', '')
                    v = v.replace(')', '')
                    status[k] = tuple(v.split())
                else:
                    status[k] = v.lstrip()
            else:
                # this is a line with only key which means a multi-line/
                # multi-value item.  Store key as List which will be
                # populated on subsequent iterations.
                status[k] = []
    return status


def is_cluster_leader(target, schema=None):
    """Retrieve status information from clustered OVSDB.

    :param target: Usually one of 'ovsdb-server', 'ovnnb_db', 'ovnsb_db', can
                   also be full path to control socket.
    :type target: str
    :param schema: Database schema name, deduced from target if not provided
    :type schema: Optional[str]
    :returns: Whether target is cluster leader
    :rtype: bool
    """
    try:
        return cluster_status(target, schema=schema).get('leader') == 'self'
    except subprocess.CalledProcessError:
        return False


def is_northd_active():
    """Query `ovn-northd` for active status.

    :returns: True if local `ovn-northd` instance is active, False otherwise
    :rtype: bool
    """
    try:
        for line in ovs_appctl('ovn-northd', 'status').splitlines():
            if line.startswith('Status:') and 'active' in line:
                return True
    except subprocess.CalledProcessError:
        pass
    return False
