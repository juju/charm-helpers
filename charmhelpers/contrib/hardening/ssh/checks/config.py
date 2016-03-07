# Copyright 2016 Canonical Limited.
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

import os

from charmhelpers.core.hookenv import (
    log,
    DEBUG,
)
from charmhelpers.fetch import (
    apt_install,
    apt_update,
)
from charmhelpers.core.host import lsb_release
from charmhelpers.contrib.hardening.audits.file import (
    TemplatedFile,
    FileContentAudit,
)
from charmhelpers.contrib.hardening.ssh import TEMPLATES_DIR
from charmhelpers.contrib.hardening import utils


def get_audits():
    """Returns the audits used to verify the ssh"""
    audits = [SSHConfig(), SSHDConfig(), SSHConfigFileContentAudit(),
              SSHDConfigFileContentAudit()]
    return audits


class SSHConfigFileContentAudit(FileContentAudit):
    def __init__(self):
        path = '/etc/ssh/ssh_config'
        super(SSHConfigFileContentAudit, self).__init__(path, {})

    def is_compliant(self, *args, **kwargs):
        self.pass_cases = []
        self.fail_cases = []
        settings = utils.get_defaults('ssh')

        if not settings['config']['client_weak_hmac']:
            self.fail_cases.append(r'^MACs\shmac-sha1[,\s]?')
        else:
            self.pass_cases.append(r'^MACs\shmac-sha1[,\s]?')

        if settings['config']['client_weak_kex']:
            self.fail_cases.append(r'^KexAlgorithms\sdiffie-hellman-group-exchange-sha256[,\s]?')
            self.pass_cases.append(r'^KexAlgorithms\sdiffie-hellman-group14-sha1[,\s]?')
            self.pass_cases.append(r'^KexAlgorithms\sdiffie-hellman-group-exchange-sha1[,\s]?')
            self.pass_cases.append(r'^KexAlgorithms\sdiffie-hellman-group1-sha1[,\s]?')
        else:
            self.pass_cases.append(r'^KexAlgorithms\sdiffie-hellman-group-exchange-sha256$')
            self.fail_cases.append(r'^KexAlgorithms\sdiffie-hellman-group14-sha1[,\s]?')
            self.fail_cases.append(r'^KexAlgorithms\sdiffie-hellman-group-exchange-sha1[,\s]?')
            self.fail_cases.append(r'^KexAlgorithms\sdiffie-hellman-group1-sha1[,\s]?')

        if settings['config']['client_cbc_required']:
            self.pass_cases.append(r'^Ciphers\s.*-cbc[,\s]?')
            self.fail_cases.append(r'^Ciphers\s.*aes128-ctr[,\s]?')
            self.fail_cases.append(r'^Ciphers\s.*aes192-ctr[,\s]?')
            self.fail_cases.append(r'^Ciphers\s.*aes256-ctr[,\s]?')
        else:
            self.fail_cases.append(r'^Ciphers\s.*-cbc[,\s]?')
            self.pass_cases.append(r'^Ciphers\s.*aes128-ctr[,\s]?')
            self.pass_cases.append(r'^Ciphers\s.*aes192-ctr[,\s]?')
            self.pass_cases.append(r'^Ciphers\s.*aes256-ctr[,\s]?')

        if settings['config']['client_roaming']:
            self.pass_cases.append(r'^UseRoaming yes$')
        else:
            self.pass_cases.append(r'^UseRoaming no$')

        super(SSHConfigFileContentAudit, self).is_compliant(*args, **kwargs)


class SSHDConfigFileContentAudit(FileContentAudit):
    def __init__(self):
        path = '/etc/ssh/sshd_config'
        super(SSHDConfigFileContentAudit, self).__init__(path, {})

    def is_compliant(self, *args, **kwargs):
        self.pass_cases = []
        self.fail_cases = []
        settings = utils.get_defaults('ssh')

        if not settings['config']['client_weak_hmac']:
            self.fail_cases.append(r'^MACs\shmac-sha1[,\s]?')
        else:
            self.pass_cases.append(r'^MACs\shmac-sha1[,\s]?')

        if settings['config']['client_weak_kex']:
            self.fail_cases.append(r'^KexAlgorithms\sdiffie-hellman-group-exchange-sha256^')
            self.pass_cases.append(r'^KexAlgorithms\sdiffie-hellman-group14-sha1[,\s]?')
            self.pass_cases.append(r'^KexAlgorithms\sdiffie-hellman-group-exchange-sha1[,\s]?')
            self.pass_cases.append(r'^KexAlgorithms\sdiffie-hellman-group1-sha1[,\s]?')
        else:
            self.pass_cases.append(r'^KexAlgorithms\sdiffie-hellman-group-exchange-sha256^')
            self.fail_cases.append(r'^KexAlgorithms\sdiffie-hellman-group14-sha1[,\s]?')
            self.fail_cases.append(r'^KexAlgorithms\sdiffie-hellman-group-exchange-sha1[,\s]?')
            self.fail_cases.append(r'^KexAlgorithms\sdiffie-hellman-group1-sha1[,\s]?')

        if settings['config']['client_cbc_required']:
            self.pass_cases.append(r'^Ciphers\s.*-cbc[,\s]?')
            self.fail_cases.append(r'^Ciphers\s.*aes128-ctr[,\s]?')
            self.fail_cases.append(r'^Ciphers\s.*aes192-ctr[,\s]?')
            self.fail_cases.append(r'^Ciphers\s.*aes256-ctr[,\s]?')
        else:
            self.fail_cases.append(r'^Ciphers\s.*-cbc[,\s]?')
            self.pass_cases.append(r'^Ciphers\s.*aes128-ctr[,\s]?')
            self.pass_cases.append(r'^Ciphers\s.*aes192-ctr[,\s]?')
            self.pass_cases.append(r'^Ciphers\s.*aes256-ctr[,\s]?')

        if settings['config']['sftp_enable']:
            self.pass_cases.append(r'^Subsystem\ssftp^')
        else:
            self.pass_cases.append(r'^#Subsystem\ssftp^')
            self.fail_cases.append(r'^Subsystem\ssftp^')

        super(SSHDConfigFileContentAudit, self).is_compliant(*args, **kwargs)


class SSHConfigContext(object):

    type = 'client'

    def get_macs(self, settings):
        if settings['%s_weak_hmac' % (self.type)]:
            weak_macs = 'weak'
        else:
            weak_macs = 'default'

        default = 'hmac-sha2-512,hmac-sha2-256,hmac-ripemd160'
        macs = {'default': default,
                'weak': default + ',hmac-sha1'}

        default = ('hmac-sha2-512-etm@openssh.com,'
                   'hmac-sha2-256-etm@openssh.com,'
                   'hmac-ripemd160-etm@openssh.com,umac-128-etm@openssh.com,'
                   'hmac-sha2-512,hmac-sha2-256,hmac-ripemd160')
        macs_66 = {'default': default,
                   'weak': default + ',hmac-sha1'}

        # use newer ciphers on ubuntu 14.04
        if lsb_release() >= "14.04":
            log("Detected Ubuntu 14.04 or newer, use new macs", level=DEBUG)
            macs = macs_66

        return macs[weak_macs]

    def get_kexs(self, settings):
        if settings['%s_weak_kex' % (self.type)]:
            weak_kex = 'weak'
        else:
            weak_kex = 'default'

        default = 'diffie-hellman-group-exchange-sha256'
        weak = (default + ',diffie-hellman-group14-sha1,'
                'diffie-hellman-group-exchange-sha1,'
                'diffie-hellman-group1-sha1')
        kex = {'default': default,
               'weak': weak}

        default = ('curve25519-sha256@libssh.org,'
                   'diffie-hellman-group-exchange-sha256')
        weak = (default + ',diffie-hellman-group14-sha1,'
                'diffie-hellman-group-exchange-sha1,'
                'diffie-hellman-group1-sha1')
        kex_66 = {'default': default,
                  'weak': weak}

        # use newer kex on ubuntu 14.04
        if lsb_release() >= "14.04":
            log('Detected Ubuntu 14.04 or newer, use new key exchange '
                'algorithms', level=DEBUG)
            kex = kex_66

        return kex[weak_kex]

    def get_ciphers(self, settings):
        if settings['%s_cbc_required' % (self.type)]:
            weak_ciphers = 'weak'
        else:
            weak_ciphers = 'default'

        default = 'aes256-ctr,aes192-ctr,aes128-ctr'
        cipher = {'default': default,
                  'weak': default + 'aes256-cbc,aes192-cbc,aes128-cbc'}

        default = ('chacha20-poly1305@openssh.com,aes256-gcm@openssh.com,'
                   'aes128-gcm@openssh.com,aes256-ctr,aes192-ctr,aes128-ctr')
        ciphers_66 = {'default': default,
                      'weak': default + ',aes256-cbc,aes192-cbc,aes128-cbc'}

        # use newer ciphers on ubuntu
        if lsb_release() >= "14.04":
            log('Detected Ubuntu 14.04 or newer, use new ciphers', level=DEBUG)
            cipher = ciphers_66

        return cipher[weak_ciphers]

    def __call__(self):
        defaults = utils.get_defaults('ssh')
        ctxt = {
            'remote_hosts': defaults['config']['remote_hosts'],
            'password_auth_allowed':
            defaults['config']['client_password_authentication'],
            'ports': defaults['config']['ports'],
            'ciphers': self.get_ciphers(defaults['config']),
            'macs': self.get_macs(defaults['config']),
            'kexs': self.get_kexs(defaults['config']),
            'roaming': defaults['config']['client_roaming'],
        }
        return ctxt


class SSHConfig(TemplatedFile):
    def __init__(self):
        path = '/etc/ssh/ssh_config'
        super(SSHConfig, self).__init__(path=path,
                                        template_dir=TEMPLATES_DIR,
                                        context=SSHConfigContext(),
                                        user='root',
                                        group='root',
                                        mode=0o0644)

    def pre_write(self):
        apt_update(fatal=True)
        apt_install('openssh-client')
        if not os.path.exists('/etc/ssh'):
            os.makedir('/etc/ssh')
            # NOTE: don't recurse
            utils.ensure_permissions('/etc/ssh', 'root', 'root', 0o0755,
                                     maxdepth=0)

    def post_write(self):
        # NOTE: don't recurse
        utils.ensure_permissions('/etc/ssh', 'root', 'root', 0o0755,
                                 maxdepth=0)


class SSHDConfigContext(SSHConfigContext):

    type = 'server'

    def __call__(self):
        defaults = utils.get_defaults('ssh')
        if defaults['general']['network_ipv6_enable']:
            addr_family = 'any'
        else:
            addr_family = 'inet'

        allow_tcp_forwarding = "no"
        if defaults['config']['allow_tcp_forwarding']:
            allow_tcp_forwarding = "yes"

        allow_x11_forwarding = "no"
        if defaults['config']['allow_x11_forwarding']:
            allow_x11_forwarding = "yes"

        allow_agent_forwarding = "no"
        if defaults['config']['allow_agent_forwarding']:
            allow_agent_forwarding = "yes"

        print_motd = "no"
        if defaults['config']['print_motd']:
            print_motd = "yes"

        print_last_log = "no"
        if defaults['config']['print_last_log']:
            print_last_log = "yes"

        ctxt = {
            'password_auth_allowed':
            defaults['config']['server_password_authentication'],
            'ports': defaults['config']['ports'],
            'addr_family': addr_family,
            'ciphers': self.get_ciphers(defaults['config']),
            'macs': self.get_macs(defaults['config']),
            'kexs': self.get_kexs(defaults['config']),
            'host_key_files': defaults['config']['host_key_files'],
            'allow_root_with_key': defaults['config']['allow_root_with_key'],
            'password_authentication':
            defaults['config']['server_password_authentication'],
            'allow_x11_forwarding': allow_x11_forwarding,
            'print_motd': print_motd,
            'print_last_log': print_last_log,
            'client_alive_interval':
            defaults['config']['client_alive_interval'],
            'client_alive_count': defaults['config']['client_alive_count'],
            'allow_tcp_forwarding': allow_tcp_forwarding,
            'allow_agent_forwarding': allow_agent_forwarding,
            'deny_users': defaults['config']['deny_users'],
            'allow_users': defaults['config']['allow_users'],
            'deny_groups': defaults['config']['deny_groups'],
            'allow_groups': defaults['config']['allow_groups'],
            'use_dns': defaults['config']['use_dns'],
            'sftp_enable': defaults['config']['sftp_enable'],
            'sftp_group': defaults['config']['sftp_group'],
            'sftp_chroot': defaults['config']['sftp_chroot'],
        }
        return ctxt


class SSHDConfig(TemplatedFile):
    def __init__(self):
        path = '/etc/ssh/sshd_config'
        super(SSHDConfig, self).__init__(path=path,
                                         template_dir=TEMPLATES_DIR,
                                         context=SSHDConfigContext(),
                                         user='root',
                                         group='root',
                                         mode=0o0600,
                                         service_actions=[{'service': 'ssh',
                                                           'actions':
                                                           ['restart']}])

    def pre_write(self):
        apt_update(fatal=True)
        apt_install('openssh-server')
        if not os.path.exists('/etc/ssh'):
            os.makedir('/etc/ssh')
            # NOTE: don't recurse
            utils.ensure_permissions('/etc/ssh', 'root', 'root', 0o0755,
                                     maxdepth=0)

    def post_write(self):
        # NOTE: don't recurse
        utils.ensure_permissions('/etc/ssh', 'root', 'root', 0o0755,
                                 maxdepth=0)
