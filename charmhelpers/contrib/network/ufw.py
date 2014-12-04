"""
This module contains helpers to add and remove ufw rules.

Examples:

- open SSH port for subnet 10.0.3.0/24:

  >>> from charmhelpers.contrib.network import ufw
  >>> ufw.enable()
  >>> ufw.grant_access(src='10.0.3.0/24', dst='any', port='22', proto='tcp')

- open service by name as defined in /etc/services:

  >>> from charmhelpers.contrib.network import ufw
  >>> ufw.enable()
  >>> ufw.service('ssh', 'open')

- close service by port number:

  >>> from charmhelpers.contrib.network import ufw
  >>> ufw.enable()
  >>> ufw.service('4949', 'close')  # munin
"""

__author__ = "Felipe Reyes <felipe.reyes@canonical.com>"

import re
import subprocess
from charmhelpers.core import hookenv


def is_enabled():
    """
    Check if `ufw` is enabled

    :returns: True if ufw is enabled
    """
    output = subprocess.check_output(['ufw', 'status'], env={'LANG': 'en_US'})

    m = re.findall(r'^Status: active\n', output, re.M)

    return len(m) >= 1


def enable():
    """
    Enable ufw

    :returns: True if ufw is successfully enabled
    """
    if is_enabled():
        return True

    output = subprocess.check_output(['ufw', 'enable'], env={'LANG': 'en_US'})

    m = re.findall('^Firewall is active and enabled on system startup\n',
                   output, re.M)
    hookenv.log(output, level='DEBUG')

    if len(m) == 0:
        hookenv.log("ufw couldn't be enabled", level='WARN')
        return False
    else:
        hookenv.log("ufw enabled", level='INFO')
        return True


def disable():
    """
    Disable ufw

    :returns: True if ufw is successfully disabled
    """
    if not is_enabled():
        return True

    output = subprocess.check_output(['ufw', 'disable'], env={'LANG': 'en_US'})

    m = re.findall(r'^Firewall stopped and disabled on system startup\n',
                   output, re.M)
    hookenv.log(output, level='DEBUG')

    if len(m) == 0:
        hookenv.log("ufw couldn't be disabled", level='WARN')
        return False
    else:
        hookenv.log("ufw disabled", level='INFO')
        return True


def modify_access(src, dst='any', port=None, proto=None, action='allow'):
    """
    Grant access to an address or subnet

    :param src: address (e.g. 192.168.1.234) or subnet
                (e.g. 192.168.1.0/24).
    :param dst: destiny of the connection, if the machine has multiple IPs and
                connections to only one of those have to accepted this is the
                field has to be set.
    :param port: destiny port
    :param proto: protocol (tcp or udp)
    :param action: `allow` or `delete`
    """
    if not is_enabled():
        hookenv.log('ufw is disabled, skipping modify_access()', level='WARN')
        return

    if action == 'delete':
        cmd = ['ufw', 'delete', 'allow']
    else:
        cmd = ['ufw', action]

    if src is not None:
        cmd += ['from', src]

    if dst is not None:
        cmd += ['to', dst]

    if port is not None:
        cmd += ['port', port]

    if proto is not None:
        cmd += ['proto', proto]

    hookenv.log('ufw {}: {}'.format(action, ' '.join(cmd)), level='DEBUG')
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    (stdout, stderr) = p.communicate()

    hookenv.log(stdout, level='INFO')

    if p.returncode != 0:
        hookenv.log(stderr, level='ERROR')
        hookenv.log('Error running: {}, exit code: {}'.format(' '.join(cmd),
                                                              p.returncode),
                    level='ERROR')


def grant_access(src, dst='any', port=None, proto=None):
    """
    Grant access to an address or subnet

    :param src: address (e.g. 192.168.1.234) or subnet
                (e.g. 192.168.1.0/24).
    :param dst: destiny of the connection, if the machine has multiple IPs and
                connections to only one of those have to accepted this is the
                field has to be set.
    :param port: destiny port
    :param proto: protocol (tcp or udp)
    """
    return modify_access(src, dst=dst, port=port, proto=proto, action='allow')


def revoke_access(src, dst='any', port=None, proto=None):
    """
    Revoke access to an address or subnet

    :param src: address (e.g. 192.168.1.234) or subnet
                (e.g. 192.168.1.0/24).
    :param dst: destiny of the connection, if the machine has multiple IPs and
                connections to only one of those have to accepted this is the
                field has to be set.
    :param port: destiny port
    :param proto: protocol (tcp or udp)
    """
    return modify_access(src, dst=dst, port=port, proto=proto, action='delete')


def service(name, action):
    """
    Open/close access to a service

    :param name: could be a service name defined in `/etc/services` or a port
                 number.
    :param action: `open` or `close`
    """
    if action == 'open':
        subprocess.check_output(['ufw', 'allow', name])
    elif action == 'close':
        subprocess.check_output(['ufw', 'delete', 'allow', name])
    else:
        raise Exception(("'{}' not supported, use 'allow' "
                         "or 'delete'").format(action))
