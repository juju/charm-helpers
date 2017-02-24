# Copyright 2014-2017 Canonical Limited.
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
"""
Charm helpers snap for classic charms.

If writing reactive charms, use the snap layer:
https://lists.ubuntu.com/archives/snapcraft/2016-September/001114.html
"""
import subprocess
from charmhelpers.core.hookenv import log

__author__ = 'Joseph Borg <joseph.borg@canonical.com>'


def _snap_exec(commands):
    """
    Execute snap commands.
    :param commands: List commands
    :return: Integer exit code
    """
    assert type(commands) == list
    proc = subprocess.Popen(
        ['snap'] + commands
    )
    proc.wait()

    if proc.returncode > 0:
        log('`snap %s` exited with a non-zero status' % ' '.join(commands),
            level='FATAL')

    return proc.returncode


def snap_install(package, edge=False, beta=False, candidate=False, stable=False, devmode=False, jailmode=False,
                 classic=False, dangerous=False, channel=None, revision=None):
    """
    Install a snap package.

    :param package: String or List String package name
    :param edge: Boolean install from the edge channel
    :param beta: Boolean install from the beta channel
    :param candidate: Boolean install from the candidate channel
    :param stable: Boolean install from the stable channel
    :param devmode: Boolean put snap in development mode and disable security confinement
    :param jailmode: Boolean put snap in enforced confinement mode
    :param classic: Boolean put snap in classic mode and disable security confinement
    :param dangerous: Boolean install the given snap file even if there are no pre-acknowledged signatures for
           it, meaning it was not verified and could be dangerous (--devmode implies this)
    :param channel: String use this channel instead of stable
    :param revision: String install the given revision of a snap, to which you must have developer access
    :return: None
    """
    if type(package) is not list:
        package = [package]

    flags = []

    if edge:
        flags.append('--edge')
    if beta:
        flags.append('--beta')
    if candidate:
        flags.append('--candidate')
    if stable:
        flags.append('--stable')
    if devmode:
        flags.append('--devmode')
    if jailmode:
        flags.append('--jailmode')
    if classic:
        flags.append('--classic')
    if dangerous:
        flags.append('--dangerous')
    if channel:
        flags.append('--channel=%s' % channel)
    if revision:
        flags.append('--revision=%s' % revision)

    message = 'Installing snap "%s"' % package
    if flags:
        message += ' with options "%s"' % ' '.join(flags)

    log(message)
    _snap_exec(['install'] + flags + package)


def snap_remove(package):
    """
    Remove a snap package.

    :param package: String or List String package name
    :return: None
    """
    if type(package) is not list:
        package = [package]

    log('Removing snap "%s"' % package)
    _snap_exec(['remove'] + package)
