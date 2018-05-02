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


def add_bridge(name, datapath_type=None):
    ''' Add the named bridge to openvswitch '''
    log('Creating bridge {}'.format(name))
    cmd = ["ovs-vsctl", "--", "--may-exist", "add-br", name]
    if datapath_type is not None:
        cmd += ['--', 'set', 'bridge', name,
                'datapath_type={}'.format(datapath_type)]
    subprocess.check_call(cmd)


def del_bridge(name):
    ''' Delete the named bridge from openvswitch '''
    log('Deleting bridge {}'.format(name))
    subprocess.check_call(["ovs-vsctl", "--", "--if-exists", "del-br", name])


def add_bridge_port(name, port, promisc=False):
    ''' Add a port to the named openvswitch bridge '''
    log('Adding port {} to bridge {}'.format(port, name))
    subprocess.check_call(["ovs-vsctl", "--", "--may-exist", "add-port",
                           name, port])
    subprocess.check_call(["ip", "link", "set", port, "up"])
    if promisc:
        subprocess.check_call(["ip", "link", "set", port, "promisc", "on"])
    else:
        subprocess.check_call(["ip", "link", "set", port, "promisc", "off"])


def del_bridge_port(name, port):
    ''' Delete a port from the named openvswitch bridge '''
    log('Deleting port {} from bridge {}'.format(port, name))
    subprocess.check_call(["ovs-vsctl", "--", "--if-exists", "del-port",
                           name, port])
    subprocess.check_call(["ip", "link", "set", port, "down"])
    subprocess.check_call(["ip", "link", "set", port, "promisc", "off"])


def add_ovsbridge_linuxbridge(name, bridge):
    ''' Add linux bridge to the named openvswitch bridge
    :param name: Name of ovs bridge to be added to Linux bridge
    :param bridge: Name of Linux bridge to be added to ovs bridge
    :returns: True if veth is added between ovs bridge and linux bridge,
    False otherwise'''
    try:
        import netifaces
    except ImportError:
        if six.PY2:
            apt_install('python-netifaces', fatal=True)
        else:
            apt_install('python3-netifaces', fatal=True)
        import netifaces

    ovsbridge_port = "veth-" + name
    linuxbridge_port = "veth-" + bridge
    log('Adding linuxbridge {} to ovsbridge {}'.format(bridge, name),
        level=INFO)
    interfaces = netifaces.interfaces()
    for interface in interfaces:
        if interface == ovsbridge_port or interface == linuxbridge_port:
            log('Interface {} already exists'.format(interface), level=INFO)
            return

    check_for_eni_source()

    with open('/etc/network/interfaces.d/{}.cfg'.format(
            linuxbridge_port), 'w') as config:
        config.write(BRIDGE_TEMPLATE.format(linuxbridge_port=linuxbridge_port,
                                            ovsbridge_port=ovsbridge_port,
                                            bridge=bridge))

    subprocess.check_call(["ifup", linuxbridge_port])
    add_bridge_port(name, linuxbridge_port)


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


def enable_ipfix(bridge, target):
    '''Enable IPfix on bridge to target.
    :param bridge: Bridge to monitor
    :param target: IPfix remote endpoint
    '''
    cmd = ['ovs-vsctl', 'set', 'Bridge', bridge, 'ipfix=@i', '--',
           '--id=@i', 'create', 'IPFIX', 'targets="{}"'.format(target)]
    log('Enabling IPfix on {}.'.format(bridge))
    subprocess.check_call(cmd)


def disable_ipfix(bridge):
    '''Diable IPfix on target bridge.
    :param bridge: Bridge to modify
    '''
    cmd = ['ovs-vsctl', 'clear', 'Bridge', bridge, 'ipfix']
    subprocess.check_call(cmd)
