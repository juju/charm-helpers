# Copyright 2019 Canonical Limited.
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

import collections
import configparser
import glob
import os.path
import subprocess

from charmhelpers.contrib.openstack.audits import (
    audit,
    AuditType,
    # filters
    is_audit_type,
    it_has_config,
)

from charmhelpers.core.hookenv import (
    cached,
)


FILE_ASSERTIONS = {
    'nova': {
        # Explicitly mentioned in security guide
        '/etc/nova/nova.conf': {
            'group': 'nova',
            'mode': '640',
        },
        '/etc/nova/api-paste.ini': {
            'group': 'nova',
            'mode': '640',
        },
        '/etc/nova/rootwrap.conf': {
            'group': 'nova',
            'mode': '640',
        },
        # Other
        '/etc/nova/nova-compute.conf': {
            'group': 'nova',
            'mode': '640',
        },
        '/etc/nova/logging.conf': {
            'group': 'nova',
            'mode': '640',
        },
        '/etc/nova/nm.conf': {
            'group': 'nova',
            'mode': '640',
        },
        '/etc/nova/*': {
            'group': 'nova',
            'mode': '640',
        },
    }
}

Ownership = collections.namedtuple('Ownership', 'owner group mode')


@cached
def _stat(file):
    """
    Get the Ownership information from a file.

    :param file: The path to a file to stat
    :type file: str
    :returns: owner, group, and mode of the specified file
    :rtype: Ownership
    :raises subprocess.CalledProcessError: If the underlying stat fails
    """
    out = subprocess.check_output(['stat', '-c', '%U %G %a', file]).decode('utf-8')
    return Ownership(*out.strip().split(' '))


@cached
def _config_ini(path):
    """
    Parse an ini file

    :param path: The path to a file to parse
    :type file: str
    :returns: Configuration contained in path
    :rtype: Dict
    """
    conf = configparser.ConfigParser()
    conf.read(path)
    return dict(conf)


def _validate_file_ownership(owner, group, file_name):
    """
    Validate that a specified file is owned by `owner:group`.

    :param owner: Name of the owner
    :type owner: str
    :param group: Name of the group
    :type group: str
    :param file_name: Path to the file to verify
    :type file_name: str
    """
    try:
        ownership = _stat(file_name)
    except subprocess.CalledProcessError as e:
        print("Error reading file: {}".format(e))
        assert False, "Specified file does not exist: {}".format(file_name)
    assert owner == ownership.owner, \
        "{} has an incorrect owner: {} should be {}".format(
            file_name, ownership.owner, owner)
    assert group == ownership.group, \
        "{} has an incorrect group: {} should be {}".format(
            file_name, ownership.group, group)
    print("Validate ownership of {}: PASS".format(file_name))


def _validate_file_mode(mode, file_name):
    """
    Validate that a specified file has the specified permissions.

    :param mode: file mode that is desires
    :type owner: str
    :param file_name: Path to the file to verify
    :type file_name: str
    """
    try:
        ownership = _stat(file_name)
    except subprocess.CalledProcessError as e:
        print("Error reading file: {}".format(e))
        assert False, "Specified file does not exist: {}".format(file_name)
    assert mode == ownership.mode, \
        "{} has an incorrect mode: {} should be {}".format(
            file_name, ownership.mode, mode)
    print("Validate mode of {}: PASS".format(file_name))


@cached
def _config_section(config, section):
    """Read the configuration file and return a section."""
    path = os.path.join(config.get('config_path'), config.get('config_file'))
    conf = _config_ini(path)
    return conf.get(section)


@audit(is_audit_type(AuditType.OpenStackSecurityGuide),
       it_has_config('files'))
def validate_file_ownership(config):
    """Verify that configuration files are owned by the correct user/group."""
    files = config.get('files', {})
    for file_name, options in files.items():
        owner = options.get('owner', config.get('owner', 'root'))
        group = options.get('group', config.get('group', 'root'))
        if '*' in file_name:
            for file in glob.glob(file_name):
                if file not in files.keys():
                    if os.path.isfile(file):
                        _validate_file_ownership(owner, group, file)
        else:
            if os.path.isfile(file_name):
                _validate_file_ownership(owner, group, file_name)


@audit(is_audit_type(AuditType.OpenStackSecurityGuide),
       it_has_config('files'))
def validate_file_permissions(config):
    """Verify that permissions on configuration files are sufficiently secure."""
    files = config.get('files', {})
    for file_name, options in files.items():
        mode = options.get('mode', config.get('permissions', '600'))
        if '*' in file_name:
            for file in glob.glob(file_name):
                if file not in files.keys():
                    if os.path.isfile(file):
                        _validate_file_mode(mode, file)
        else:
            if os.path.isfile(file_name):
                _validate_file_mode(mode, file_name)


@audit(is_audit_type(AuditType.OpenStackSecurityGuide))
def validate_uses_keystone(audit_options):
    """Validate that the service uses Keystone for authentication."""
    section = _config_section(audit_options, 'DEFAULT')
    assert section is not None, "Missing section 'DEFAULT'"
    assert section.get('auth_strategy') == "keystone", \
        "Application is not using Keystone"


@audit(is_audit_type(AuditType.OpenStackSecurityGuide))
def validate_uses_tls_for_keystone(audit_options):
    """Verify that TLS is used to communicate with Keystone."""
    section = _config_section(audit_options, 'keystone_authtoken')
    assert section is not None, "Missing section 'keystone_authtoken'"
    assert not section.get('insecure') and \
        "https://" in section.get("auth_uri"), \
        "TLS is not used for Keystone"


@audit(is_audit_type(AuditType.OpenStackSecurityGuide))
def validate_uses_tls_for_glance(audit_options):
    """Verify that TLS is used to communicate with Glance."""
    section = _config_section(audit_options, 'glance')
    assert section is not None, "Missing section 'glance'"
    assert not section.get('insecure') and \
        "https://" in section.get("api_servers"), \
        "TLS is not used for Glance"
