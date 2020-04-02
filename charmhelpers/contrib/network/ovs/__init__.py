# Copyright 2014-2015 Canonical Limited.
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

''' Helpers for interacting with OpenvSwitch '''
import hashlib
import subprocess
import os
import six

from charmhelpers.fetch import apt_install


from charmhelpers.core.hookenv import (
    log, WARNING, INFO, DEBUG
)
from charmhelpers.core.host import (
    service
)


BRIDGE_TEMPLATE = """\
# This veth pair is required when neutron data-port is mapped to an existing linux bridge. lp:1635067

auto {linuxbridge_port}
iface {linuxbridge_port} inet manual
    pre-up ip link add name {linuxbridge_port} type veth peer name {ovsbridge_port}
    pre-up ip link set {ovsbridge_port} master {bridge}
    pre-up ip link set {ovsbridge_port} up
    up ip link set {linuxbridge_port} up
    down ip link del {linuxbridge_port}
"""

MAX_KERNEL_INTERFACE_NAME_LEN = 15


def get_bridges():
    """Return list of the bridges on the default openvswitch

    :returns: List of bridge names
    :rtype: List[str]
    :raises: subprocess.CalledProcessError if ovs-vsctl fails
    """
    cmd = ["ovs-vsctl", "list-br"]
    lines = subprocess.check_output(cmd).decode('utf-8').split("\n")
    maybe_bridges = [l.strip() for l in lines]
    return [b for b in maybe_bridges if b]


def get_bridge_ports(name):
    """Return a list the ports on a named bridge

    :param name: the name of the bridge to list
    :type name: str
    :returns: List of ports on the named bridge
    :rtype: List[str]
    :raises: subprocess.CalledProcessError if the ovs-vsctl command fails. If
        the named bridge doesn't exist, then the exception will be raised.
    """
    cmd = ["ovs-vsctl", "--", "list-ports", name]
    lines = subprocess.check_output(cmd).decode('utf-8').split("\n")
    maybe_ports = [l.strip() for l in lines]
    return [p for p in maybe_ports if p]


def get_bridges_and_ports_map():
    """Return dictionary of bridge to ports for the default openvswitch

    :returns: a mapping of bridge name to a list of ports.
    :rtype: Dict[str, List[str]]
    :raises: subprocess.CalledProcessError if any of the underlying ovs-vsctl
        command fail.
    """
    return {b: get_bridge_ports(b) for b in get_bridges()}


def _dict_to_vsctl_set(data, table, entity):
    """Helper that takes dictionary and provides ``ovs-vsctl set`` commands

    :param data: Additional data to attach to interface
        The keys in the data dictionary map directly to column names in the
        OpenvSwitch table specified as defined in DB-SCHEMA [0] referenced in
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
    :type data: Optional[Dict[str,Union[str,Dict[str,str]]]]
    :param table: Name of table to operate on
    :type table: str
    :param entity: Name of entity to operate on
    :type entity: str
    :returns: '--' separated ``ovs-vsctl set`` commands
    :rtype: Iterator[Tuple[str, str, str, str, str]]
    """
    for (k, v) in data.items():
        if isinstance(v, dict):
            entries = {
                '{}:{}'.format(k, dk): dv for (dk, dv) in v.items()}
        else:
            entries = {k: v}
        for (colk, colv) in entries.items():
            yield ('--', 'set', table, entity, '{}={}'.format(colk, colv))


def add_bridge(name, datapath_type=None, brdata=None, exclusive=False):
    """Add the named bridge to openvswitch and set/update bridge data for it

    :param name: Name of bridge to create
    :type name: str
    :param datapath_type: Add datapath_type to bridge (DEPRECATED, use brdata)
    :type datapath_type: Optional[str]
    :param brdata: Additional data to attach to bridge
        The keys in the brdata dictionary map directly to column names in the
        OpenvSwitch bridge table as defined in DB-SCHEMA [0] referenced in
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
    :type brdata: Optional[Dict[str,Union[str,Dict[str,str]]]]
    :param exclusive: If True, raise exception if bridge exists
    :type exclusive: bool
    :raises: subprocess.CalledProcessError
    """
    log('Creating bridge {}'.format(name))
    cmd = ['ovs-vsctl', '--']
    if not exclusive:
        cmd.append('--may-exist')
    cmd.extend(('add-br', name))
    if brdata:
        for setcmd in _dict_to_vsctl_set(brdata, 'bridge', name):
            cmd.extend(setcmd)
    if datapath_type is not None:
        log('DEPRECATION WARNING: add_bridge called with datapath_type, '
            'please use the brdata keyword argument instead.')
        cmd += ['--', 'set', 'bridge', name,
                'datapath_type={}'.format(datapath_type)]
    subprocess.check_call(cmd)


def del_bridge(name):
    """Delete the named bridge from openvswitch

    :param name: Name of bridge to remove
    :type name: str
    :raises: subprocess.CalledProcessError
    """
    log('Deleting bridge {}'.format(name))
    subprocess.check_call(["ovs-vsctl", "--", "--if-exists", "del-br", name])


def add_bridge_port(name, port, promisc=False, ifdata=None, exclusive=False,
                    linkup=True):
    """Add port to bridge and optionally set/update interface data for it

    :param name: Name of bridge to attach port to
    :type name: str
    :param port: Name of port as represented in netdev
    :type port: str
    :param promisc: Whether to set promiscuous mode on interface
    :type promisc: bool
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
    :param linkup: Bring link up
    :type linkup: bool
    :raises: subprocess.CalledProcessError
    """
    cmd = ['ovs-vsctl', '--']
    if not exclusive:
        cmd.append('--may-exist')
    cmd.extend(('add-port', name, port))
    if ifdata:
        for setcmd in _dict_to_vsctl_set(ifdata, 'Interface', port):
            cmd.extend(setcmd)

    log('Adding port {} to bridge {}'.format(port, name))
    subprocess.check_call(cmd)
    if linkup:
        # This is mostly a workaround for CI environments, in the real world
        # the bare metal provider would most likely have configured and brought
        # up the link for us.
        subprocess.check_call(["ip", "link", "set", port, "up"])
    if promisc:
        subprocess.check_call(["ip", "link", "set", port, "promisc", "on"])
    else:
        subprocess.check_call(["ip", "link", "set", port, "promisc", "off"])


def del_bridge_port(name, port):
    """Delete a port from the named openvswitch bridge

    :param name: Name of bridge to remove port from
    :type name: str
    :param port: Name of port to remove
    :type port: str
    :raises: subprocess.CalledProcessError
    """
    log('Deleting port {} from bridge {}'.format(port, name))
    subprocess.check_call(["ovs-vsctl", "--", "--if-exists", "del-port",
                           name, port])
    subprocess.check_call(["ip", "link", "set", port, "down"])
    subprocess.check_call(["ip", "link", "set", port, "promisc", "off"])


def add_ovsbridge_linuxbridge(name, bridge, ifdata=None):
    """Add linux bridge to the named openvswitch bridge

    :param name: Name of ovs bridge to be added to Linux bridge
    :type name: str
    :param bridge: Name of Linux bridge to be added to ovs bridge
    :type name: str
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
    """
    try:
        import netifaces
    except ImportError:
        if six.PY2:
            apt_install('python-netifaces', fatal=True)
        else:
            apt_install('python3-netifaces', fatal=True)
        import netifaces

    # NOTE(jamespage):
    # Older code supported addition of a linuxbridge directly
    # to an OVS bridge; ensure we don't break uses on upgrade
    existing_ovs_bridge = port_to_br(bridge)
    if existing_ovs_bridge is not None:
        log('Linuxbridge {} is already directly in use'
            ' by OVS bridge {}'.format(bridge, existing_ovs_bridge),
            level=INFO)
        return

    # NOTE(jamespage):
    # preserve existing naming because interfaces may already exist.
    ovsbridge_port = "veth-" + name
    linuxbridge_port = "veth-" + bridge
    if (len(ovsbridge_port) > MAX_KERNEL_INTERFACE_NAME_LEN or
            len(linuxbridge_port) > MAX_KERNEL_INTERFACE_NAME_LEN):
        # NOTE(jamespage):
        # use parts of hashed bridgename (openstack style) when
        # a bridge name exceeds 15 chars
        hashed_bridge = hashlib.sha256(bridge.encode('UTF-8')).hexdigest()
        base = '{}-{}'.format(hashed_bridge[:8], hashed_bridge[-2:])
        ovsbridge_port = "cvo{}".format(base)
        linuxbridge_port = "cvb{}".format(base)

    interfaces = netifaces.interfaces()
    for interface in interfaces:
        if interface == ovsbridge_port or interface == linuxbridge_port:
            log('Interface {} already exists'.format(interface), level=INFO)
            return

    log('Adding linuxbridge {} to ovsbridge {}'.format(bridge, name),
        level=INFO)

    check_for_eni_source()

    with open('/etc/network/interfaces.d/{}.cfg'.format(
            linuxbridge_port), 'w') as config:
        config.write(BRIDGE_TEMPLATE.format(linuxbridge_port=linuxbridge_port,
                                            ovsbridge_port=ovsbridge_port,
                                            bridge=bridge))

    subprocess.check_call(["ifup", linuxbridge_port])
    add_bridge_port(name, linuxbridge_port, ifdata=ifdata)


def is_linuxbridge_interface(port):
    ''' Check if the interface is a linuxbridge bridge
    :param port: Name of an interface to check whether it is a Linux bridge
    :returns: True if port is a Linux bridge'''

    if os.path.exists('/sys/class/net/' + port + '/bridge'):
        log('Interface {} is a Linux bridge'.format(port), level=DEBUG)
        return True
    else:
        log('Interface {} is not a Linux bridge'.format(port), level=DEBUG)
        return False


def set_manager(manager):
    ''' Set the controller for the local openvswitch '''
    log('Setting manager for local ovs to {}'.format(manager))
    subprocess.check_call(['ovs-vsctl', 'set-manager',
                           'ssl:{}'.format(manager)])


def set_Open_vSwitch_column_value(column_value):
    """
    Calls ovs-vsctl and sets the 'column_value' in the Open_vSwitch table.

    :param column_value:
            See http://www.openvswitch.org//ovs-vswitchd.conf.db.5.pdf for
            details of the relevant values.
    :type str
    :raises CalledProcessException: possibly ovsdb-server is not running
    """
    log('Setting {} in the Open_vSwitch table'.format(column_value))
    subprocess.check_call(['ovs-vsctl', 'set', 'Open_vSwitch', '.', column_value])


CERT_PATH = '/etc/openvswitch/ovsclient-cert.pem'


def get_certificate():
    ''' Read openvswitch certificate from disk '''
    if os.path.exists(CERT_PATH):
        log('Reading ovs certificate from {}'.format(CERT_PATH))
        with open(CERT_PATH, 'r') as cert:
            full_cert = cert.read()
            begin_marker = "-----BEGIN CERTIFICATE-----"
            end_marker = "-----END CERTIFICATE-----"
            begin_index = full_cert.find(begin_marker)
            end_index = full_cert.rfind(end_marker)
            if end_index == -1 or begin_index == -1:
                raise RuntimeError("Certificate does not contain valid begin"
                                   " and end markers.")
            full_cert = full_cert[begin_index:(end_index + len(end_marker))]
            return full_cert
    else:
        log('Certificate not found', level=WARNING)
        return None


def check_for_eni_source():
    ''' Juju removes the source line when setting up interfaces,
    replace if missing '''

    with open('/etc/network/interfaces', 'r') as eni:
        for line in eni:
            if line == 'source /etc/network/interfaces.d/*':
                return
    with open('/etc/network/interfaces', 'a') as eni:
        eni.write('\nsource /etc/network/interfaces.d/*')


def full_restart():
    ''' Full restart and reload of openvswitch '''
    if os.path.exists('/etc/init/openvswitch-force-reload-kmod.conf'):
        service('start', 'openvswitch-force-reload-kmod')
    else:
        service('force-reload-kmod', 'openvswitch-switch')


def enable_ipfix(bridge, target,
                 cache_active_timeout=60,
                 cache_max_flows=128,
                 sampling=64):
    '''Enable IPFIX on bridge to target.
    :param bridge: Bridge to monitor
    :param target: IPFIX remote endpoint
    :param cache_active_timeout: The maximum period in seconds for
                                 which an IPFIX flow record is cached
                                 and aggregated before being sent
    :param cache_max_flows: The maximum number of IPFIX flow records
                            that can be cached at a time
    :param sampling: The rate at which packets should be sampled and
                     sent to each target collector
    '''
    cmd = [
        'ovs-vsctl', 'set', 'Bridge', bridge, 'ipfix=@i', '--',
        '--id=@i', 'create', 'IPFIX',
        'targets="{}"'.format(target),
        'sampling={}'.format(sampling),
        'cache_active_timeout={}'.format(cache_active_timeout),
        'cache_max_flows={}'.format(cache_max_flows),
    ]
    log('Enabling IPfix on {}.'.format(bridge))
    subprocess.check_call(cmd)


def disable_ipfix(bridge):
    '''Diable IPFIX on target bridge.
    :param bridge: Bridge to modify
    '''
    cmd = ['ovs-vsctl', 'clear', 'Bridge', bridge, 'ipfix']
    subprocess.check_call(cmd)


def port_to_br(port):
    '''Determine the bridge that contains a port
    :param port: Name of port to check for
    :returns str: OVS bridge containing port or None if not found
    '''
    try:
        return subprocess.check_output(
            ['ovs-vsctl', 'port-to-br', port]
        ).decode('UTF-8').strip()
    except subprocess.CalledProcessError:
        return None


def ovs_appctl(target, args):
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
    cmd = ['ovs-appctl', '-t', target]
    cmd.extend(args)
    return subprocess.check_output(cmd, universal_newlines=True)
