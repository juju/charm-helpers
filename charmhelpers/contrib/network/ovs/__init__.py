''' Helpers for interacting with OpenvSwitch '''
import subprocess
import os
from charmhelpers.core.hookenv import (
    log, WARNING
)
from charmhelpers.core.host import (
    service
)


def add_bridge(name):
    ''' Add the named bridge to openvswitch '''
    log('Creating bridge {}'.format(name))
    subprocess.check_call(["ovs-vsctl", "--", "--may-exist", "add-br", name])


def del_bridge(name):
    ''' Delete the named bridge from openvswitch '''
    log('Deleting bridge {}'.format(name))
    subprocess.check_call(["ovs-vsctl", "--", "--if-exists", "del-br", name])


def add_bridge_port(name, port):
    ''' Add a port to the named openvswitch bridge '''
    log('Adding port {} to bridge {}'.format(port, name))
    subprocess.check_call(["ovs-vsctl", "--", "--may-exist", "add-port",
                           name, port])
    subprocess.check_call(["ip", "link", "set", port, "up"])


def del_bridge_port(name, port):
    ''' Delete a port from the named openvswitch bridge '''
    log('Deleting port {} from bridge {}'.format(port, name))
    subprocess.check_call(["ovs-vsctl", "--", "--if-exists", "del-port",
                           name, port])
    subprocess.check_call(["ip", "link", "set", port, "down"])


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


def full_restart():
    ''' Full restart and reload of openvswitch '''
    if os.path.exists('/etc/init/openvswitch-force-reload-kmod.conf'):
        service('start', 'openvswitch-force-reload-kmod')
    else:
        service('force-reload-kmod', 'openvswitch-switch')
