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
import json
import os
import subprocess
import uuid


def _run(*args):
    """Run a process, check result, capture decoded output from STDERR/STDOUT.

    :param args: Command and arguments to run
    :type args: Tuple[str, ...]
    :returns: Information about the completed process
    :rtype: str
    :raises subprocess.CalledProcessError
    """
    return subprocess.check_output(args, stderr=subprocess.STDOUT,
                                   universal_newlines=True)


def ovn_rundir():
    """Determine path to OVN sockets.

    Prior to OVN 20.03 the default placement of OVN sockets was together with
    Open vSwitch, from 20.03 and onwards they are kept in a separate directory.

    :returns: path to OVN rundir
    :rtype: str
    """
    OVN_RUNDIR = '/var/run/ovn'
    OVS_RUNDIR = '/var/run/openvswitch'
    for rundir in OVN_RUNDIR, OVS_RUNDIR:
        if os.path.exists(rundir):
            return (rundir)
    # Fall back to new default
    return OVN_RUNDIR


def ovn_sysconfdir():
    """Determine path to OVN configuration.

    Prior to OVN 20.03 the default placement of OVN configuration was together
    with Open vSwitch, from 20.03 and onwards they are kept in a separate
    directory.

    :returns: path to OVN sysconfdir
    :rtype: str
    """
    OVN_SYSCONFDIR = '/etc/ovn'
    OVS_SYSCONFDIR = '/etc/openvswitch'
    for sysconfdir in OVN_SYSCONFDIR, OVS_SYSCONFDIR:
        if os.path.exists(sysconfdir):
            return (sysconfdir)
    # Fall back to new default
    return OVN_SYSCONFDIR


# TODO: Make use of the new `ovn-appctl` if/when that makes sense
def ovs_appctl(target, *args):
    """Run `ovs-appctl` for target with args and return output.

    :param target: Name of daemon to contact.  Unless target begins with '/',
                   `ovs-appctl` looks for a pidfile and will build the path to
                   a /var/run/openvswitch/target.pid.ctl for you.
    :type target: str
    :param args: Command and arguments to pass to `ovs-appctl`
    :type args: Tuple[str, ...]
    :returns: Output from command
    :rtype: str
    :raises: subprocess.CalledProcessError
    """
    # NOTE(fnordahl): The ovsdb-server processes for the OVN databases use a
    # non-standard naming scheme for their daemon control socket and we need
    # to pass the full path to the socket.
    if target in ('ovnnb_db', 'ovnsb_db',):
        target = os.path.join(ovn_rundir(), target + '.ctl')
    return _run('ovs-appctl', '-t', target, *args)


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
            status[k].append(line.lstrip())
        elif ':' in line:
            k, v = line.split(':', 1)
            k = k.lower()
            k = k.replace(' ', '_')
            if v:
                if k in ('cluster_id', 'server_id',):
                    v = v.replace('(', '')
                    v = v.replace(')', '')
                    status[k] = tuple(v.split())
                else:
                    status[k] = v.lstrip()
            else:
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


def add_br(bridge, external_id=None):
    """Add bridge and optionally attach a external_id to bridge.

    :param bridge: Name of bridge to create
    :type bridge: str
    :param external_id: Key-value pair
    :type external_id: Optional[Tuple[str,str]]
    :raises: subprocess.CalledProcessError
    """
    cmd = ['ovs-vsctl', 'add-br', bridge, '--', 'set', 'bridge', bridge,
           'protocols=OpenFlow13']
    if external_id:
        cmd.extend(('--', 'br-set-external-id', bridge))
        cmd.extend(external_id)
    _run(*cmd)


def del_br(bridge):
    """Remove bridge.

    :param bridge: Name of bridge to remove
    :type bridge: str
    :raises: subprocess.CalledProcessError
    """
    _run('ovs-vsctl', 'del-br', bridge)


def add_port(bridge, port, ifdata=None, exclusive=False):
    """Add port to bridge and optionally set/update interface data for it

    :param bridge: Name of bridge to attach port to
    :type bridge: str
    :param port: Name of port as represented in netdev
    :type port: str
    :param ifdata: Additional data to attach to interface
        The keys in the ifdata dictionary map directly to column names in the
        OpenvSwitch Interface table as defined in DB-SCHEMA [0] referenced in
        RFC 7047 [1]

        There are some established conventions for keys in the external-ids
        column of various tables, consult the OVS Integration Guide [2] for
        more details.

        NOTE(fnordahl): Technically the ``external-ids`` column is called
        ``external_ids`` (with an underscore) and we rely on ``ovs-vsctl``'s
        behaviour of transforming dashes to underscores for us [3] so we can
        have a more pleasant data structure.

        0: http://www.openvswitch.org/ovs-vswitchd.conf.db.5.pdf
        1: https://tools.ietf.org/html/rfc7047
        2: http://docs.openvswitch.org/en/latest/topics/integration/
        3: https://github.com/openvswitch/ovs/blob/
               20dac08fdcce4b7fda1d07add3b346aa9751cfbc/
                   lib/db-ctl-base.c#L189-L215
    :type ifdata: Optional[Dict[str,Union[str,Dict[str,str]]]]
    :param exclusive: If True, raise exception if port exists
    :type exclusive: bool
    :raises: subprocess.CalledProcessError
    """
    cmd = ['ovs-vsctl']
    if not exclusive:
        cmd.extend(('--may-exist',))
    cmd.extend(('add-port', bridge, port))
    if ifdata:
        for (k, v) in ifdata.items():
            if isinstance(v, dict):
                entries = {
                    '{}:{}'.format(k, dk): dv for (dk, dv) in v.items()}
            else:
                entries = {k: v}
            for (colk, colv) in entries.items():
                cmd.extend(
                    ('--', 'set', 'Interface', port,
                        '{}={}'.format(colk, colv)))
    _run(*cmd)


def del_port(bridge, port):
    """Remove port from bridge.

    :param bridge: Name of bridge to remove port from
    :type bridge: str
    :param port: Name of port to remove
    :type port: str
    :raises: subprocess.CalledProcessError
    """
    _run('ovs-vsctl', 'del-port', bridge, port)


def list_ports(bridge):
    """List ports on a bridge.

    :param bridge: Name of bridge to list ports on
    :type bridge: str
    :returns: List of ports
    :rtype: List
    """
    output = _run('ovs-vsctl', 'list-ports', bridge)
    return output.splitlines()


class SimpleOVSDB(object):
    """Simple interface to OVSDB through the use of command line tools.

    OVS and OVN is managed through a set of databases.  These databases have
    similar command line tools to manage them.  We make use of the similarity
    to provide a generic class that can be used to manage them.

    The OpenvSwitch project does provide a Python API, but on the surface it
    appears to be a bit too involved for our simple use case.

    Examples:
    chassis = SimpleOVSDB('ovn-sbctl', 'chassis')
    for chs in chassis:
        print(chs)

    bridges = SimpleOVSDB('ovs-vsctl', 'bridge')
    for br in bridges:
        if br['name'] == 'br-test':
            bridges.set(br['uuid'], 'external_ids:charm', 'managed')
    """

    def __init__(self, tool, table):
        """SimpleOVSDB constructor

        :param tool: Which tool with database commands to operate on.
                     Usually one of `ovs-vsctl`, `ovn-nbctl`, `ovn-sbctl`
        :type tool: str
        :param table: Which table to operate on
        :type table: str
        """
        self.tool = tool
        self.tbl = table

    def _find_tbl(self, condition=None):
        """Run and parse output of OVSDB `find` command.

        :param condition: An optional RFC 7047 5.1 match condition
        :type condition: Optional[str]
        :returns: Dictionary with data
        :rtype: Dict[str, any]
        """
        # When using json formatted output to OVS commands Internal OVSDB
        # notation may occur that require further deserializing.
        # Reference: https://tools.ietf.org/html/rfc7047#section-5.1
        ovs_type_cb_map = {
            'uuid': uuid.UUID,
            # FIXME sets also appear to sometimes contain type/value tuples
            'set': list,
            'map': dict,
        }
        cmd = [self.tool, '-f', 'json', 'find', self.tbl]
        if condition:
            cmd.append(condition)
        output = _run(*cmd)
        data = json.loads(output)
        for row in data['data']:
            values = []
            for col in row:
                if isinstance(col, list):
                    f = ovs_type_cb_map.get(col[0], str)
                    values.append(f(col[1]))
                else:
                    values.append(col)
            yield dict(zip(data['headings'], values))

    def __iter__(self):
        return self._find_tbl()

    def clear(self, rec, col):
        _run(self.tool, 'clear', self.tbl, rec, col)

    def find(self, condition):
        return self._find_tbl(condition=condition)

    def remove(self, rec, col, value):
        _run(self.tool, 'remove', self.tbl, rec, col, value)

    def set(self, rec, col, value):
        _run(self.tool, 'set', self.tbl, rec, '{}={}'.format(col, value))
