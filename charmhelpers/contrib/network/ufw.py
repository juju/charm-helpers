# Copyright 2014-2015 Canonical Limited.
#
# This file is part of charm-helpers.
#
# charm-helpers is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version 3 as
# published by the Free Software Foundation.
#
# charm-helpers is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with charm-helpers.  If not, see <http://www.gnu.org/licenses/>.

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
import re
import os
import subprocess
from charmhelpers.core import hookenv

__author__ = "Felipe Reyes <felipe.reyes@canonical.com>"


class UFWError(Exception):
    pass


class UFWIPv6Error(UFWError):
    pass


def is_enabled():
    """
    Check if `ufw` is enabled

    :returns: True if ufw is enabled
    """
    output = subprocess.check_output(['ufw', 'status'],
                                     universal_newlines=True,
                                     env={'LANG': 'en_US',
                                          'PATH': os.environ['PATH']})

    m = re.findall(r'^Status: active\n', output, re.M)

    return len(m) >= 1


def is_ipv6_ok(soft_fail=False):
    """
    Check if IPv6 support is present and ip6tables functional

    :param soft_fail: If set to True and IPv6 support is broken, then reports
                      that the host doesn't have IPv6 support, otherwise a
                      UFWIPv6Error exception is raised.
    :returns: True if IPv6 is working, False otherwise
    """

    # do we have IPv6 in the machine?
    if os.path.isdir('/proc/sys/net/ipv6'):
        # is ip6tables kernel module loaded?
        lsmod = subprocess.check_output(['lsmod'], universal_newlines=True)
        matches = re.findall('^ip6_tables[ ]+', lsmod, re.M)
        if len(matches) == 0:
            # ip6tables support isn't complete, let's try to load it
            try:
                subprocess.check_output(['modprobe', 'ip6_tables'],
                                        universal_newlines=True)
                # great, we could load the module
                return True
            except subprocess.CalledProcessError as ex:
                hookenv.log("Couldn't load ip6_tables module: %s" % ex.output,
                            level="WARN")
                # we are in a world where ip6tables isn't working
                if soft_fail:
                    # so we inform that the machine doesn't have IPv6
                    return False
                else:
                    raise UFWIPv6Error("IPv6 firewall support broken")
        else:
            # the module is present :)
            return True

    else:
        # the system doesn't have IPv6
        return False


def disable_ipv6():
    """
    Disable ufw IPv6 support in /etc/default/ufw
    """
    exit_code = subprocess.call(['sed', '-i', 's/IPV6=.*/IPV6=no/g',
                                 '/etc/default/ufw'])
    if exit_code == 0:
        hookenv.log('IPv6 support in ufw disabled', level='INFO')
    else:
        hookenv.log("Couldn't disable IPv6 support in ufw", level="ERROR")
        raise UFWError("Couldn't disable IPv6 support in ufw")


def enable(soft_fail=False):
    """
    Enable ufw

    :param soft_fail: If set to True silently disables IPv6 support in ufw,
                      otherwise a UFWIPv6Error exception is raised when IP6
                      support is broken.
    :returns: True if ufw is successfully enabled
    """
    if is_enabled():
        return True

    if not is_ipv6_ok(soft_fail):
        disable_ipv6()

    output = subprocess.check_output(['ufw', 'enable'],
                                     universal_newlines=True,
                                     env={'LANG': 'en_US',
                                          'PATH': os.environ['PATH']})

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

    output = subprocess.check_output(['ufw', 'disable'],
                                     universal_newlines=True,
                                     env={'LANG': 'en_US',
                                          'PATH': os.environ['PATH']})

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
        cmd += ['port', str(port)]

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
        subprocess.check_output(['ufw', 'allow', str(name)],
                                universal_newlines=True)
    elif action == 'close':
        subprocess.check_output(['ufw', 'delete', 'allow', str(name)],
                                universal_newlines=True)
    else:
        raise UFWError(("'{}' not supported, use 'allow' "
                        "or 'delete'").format(action))
