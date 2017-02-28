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
        log(
            '`snap %s` exited with a non-zero status' % ' '.join(commands),
            level='FATAL'
        )

    return proc.returncode


def snap_install(packages, *flags):
    """
    Install a snap package.

    :param packages: String or List String package name
    :param flags: List String flags to pass to install command
    :return: Integer return code from snap
    """
    if type(packages) is not list:
        packages = [packages]

    flags = list(flags)

    message = 'Installing snap(s) "%s"' % ', '.join(packages)
    if flags:
        message += ' with option(s) "%s"' % ', '.join(flags)

    log(message)
    return _snap_exec(['install'] + flags + packages)


def snap_remove(packages, *flags):
    """
    Remove a snap package.

    :param packages: String or List String package name
    :param flags: List String flags to pass to remove command
    :return: Integer return code from snap
    """
    if type(packages) is not list:
        packages = [packages]

    flags = list(flags)

    message = 'Removing snap(s) "%s"' % ', '.join(packages)
    if flags:
        message += ' with options "%s"' % ', '.join(flags)

    log(message)
    return _snap_exec(['remove'] + flags + packages)


def snap_refresh(packages, *flags):
    """
    Refresh / Update snap package.

    :param packages: String or List String package name
    :param flags: List String flags to pass to refresh command
    :return: Integer return code from snap
    """
    if type(packages) is not list:
        packages = [packages]

    flags = list(flags)

    message = 'Refreshing snap(s) "%s"' % ', '.join(packages)
    if flags:
        message += ' with options "%s"' % ', '.join(flags)

    log(message)
    return _snap_exec(['refresh'] + flags + packages)
