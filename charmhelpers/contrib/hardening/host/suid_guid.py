import os
import subprocess

from charmhelpers.core.hookenv import (
    log,
    DEBUG,
    INFO,
)
from charmhelpers.contrib.hardening import (
    utils,
)

BLACKLIST = ['/usr/bin/rcp', '/usr/bin/rlogin', '/usr/bin/rsh',
             '/usr/libexec/openssh/ssh-keysign',
             '/usr/lib/openssh/ssh-keysign',
             '/sbin/netreport',
             '/usr/sbin/usernetctl',
             '/usr/sbin/userisdnctl',
             '/usr/sbin/pppd',
             '/usr/bin/lockfile',
             '/usr/bin/mail-lock',
             '/usr/bin/mail-unlock',
             '/usr/bin/mail-touchlock',
             '/usr/bin/dotlockfile',
             '/usr/bin/arping',
             '/usr/sbin/uuidd',
             '/usr/bin/mtr',
             '/usr/lib/evolution/camel-lock-helper-1.2',
             '/usr/lib/pt_chown',
             '/usr/lib/eject/dmcrypt-get-device',
             '/usr/lib/mc/cons.saver']

WHITELIST = ['/bin/mount', '/bin/ping', '/bin/su', '/bin/umount',
             '/sbin/pam_timestamp_check', '/sbin/unix_chkpwd', '/usr/bin/at',
             '/usr/bin/gpasswd', '/usr/bin/locate', '/usr/bin/newgrp',
             '/usr/bin/passwd', '/usr/bin/ssh-agent',
             '/usr/libexec/utempter/utempter', '/usr/sbin/lockdev',
             '/usr/sbin/sendmail.sendmail', '/usr/bin/expiry',
             '/bin/ping6', '/usr/bin/traceroute6.iputils',
             '/sbin/mount.nfs', '/sbin/umount.nfs',
             '/sbin/mount.nfs4', '/sbin/umount.nfs4',
             '/usr/bin/crontab',
             '/usr/bin/wall', '/usr/bin/write',
             '/usr/bin/screen',
             '/usr/bin/mlocate',
             '/usr/bin/chage', '/usr/bin/chfn', '/usr/bin/chsh',
             '/bin/fusermount',
             '/usr/bin/pkexec',
             '/usr/bin/sudo', '/usr/bin/sudoedit',
             '/usr/sbin/postdrop', '/usr/sbin/postqueue',
             '/usr/sbin/suexec',
             '/usr/lib/squid/ncsa_auth', '/usr/lib/squid/pam_auth',
             '/usr/kerberos/bin/ksu',
             '/usr/sbin/ccreds_validate',
             '/usr/bin/Xorg',
             '/usr/bin/X',
             '/usr/lib/dbus-1.0/dbus-daemon-launch-helper',
             '/usr/lib/vte/gnome-pty-helper',
             '/usr/lib/libvte9/gnome-pty-helper',
             '/usr/lib/libvte-2.90-9/gnome-pty-helper']


def suid_guid_harden():
    defaults = utils.get_defaults('os')
    if not defaults.get('security_suid_sgid_enforce'):
        log("Skipping suid/guid hardening", level=INFO)
        return

    log("Applying suid/guid hardening", level=INFO)
    u_b = defaults.get('security_suid_sgid_blacklist', [])
    u_w = defaults.get('security_suid_sgid_whitelist', [])

    blacklist = set(BLACKLIST) - set(u_w + u_b)
    whitelist = set(WHITELIST) - set(u_b + u_w)

    for path in blacklist:
        if os.path.exists(path):
            log("Removing suid/guid from %s" % (path), level=DEBUG)
            subprocess.check_call(['chmod', '-s', path])

    if not defaults.get('security_suid_sgid_remove_from_unknown'):
        return

    root_path = defaults.get('env_root_path', '/')
    cmd = ['find', root_path, '-perm', '-4000', '-o', '-perm', '-2000',
           '-type', 'f', '!', '-path', '/proc/*', '-print']
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, _ = p.communicate()
    for path in out.split('\n'):
        if os.path.exists(path) and path not in whitelist:
            log("Removing suid/guid from %s" % (path), level=DEBUG)
            subprocess.check_call(['chmod', '-s', path])
