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

"""OpenStack Security Audit code"""

import apt_pkg
#  noqa below is because we import apt for a side-effect
#  initializing apt_pkg.version_compare's _system
import apt # noqa: F401,E261
import collections
from enum import Enum
import traceback

from charmhelpers.fetch.ubuntu import get_upstream_version


class AuditType(Enum):
    OpenStackSecurityGuide = 1


_audits = {}

Audit = collections.namedtuple('Audit', 'func filters')


def audit(*args):
    """Decorator to register an audit.

    These are used to generate audits that can be run on a
    deployed system that matches the given configuration

    :param args: List of functions to filter tests against
    :type args: List[Callable(Config)]
    """
    def wrapper(f):
        test_name = f.__name__
        if _audits.get(test_name):
            raise RuntimeError(
                "Test name '{}' used more than once ?"
                .format(test_name))
        _audits[test_name] = Audit(func=f, filters=args)
        return f
    return wrapper


def is_audit_type(*args):
    """This audit is included in the specified kinds of audits."""
    def should_run(config):
        if config.get('audit_type') in args:
            return True
        else:
            return False
    return should_run


def since_package(pkg, pkg_version):
    """This audit should be run after the specified package version (incl)."""
    return lambda config=None: not before_package(pkg, pkg_version)()


def before_package(pkg, pkg_version):
    """This audit should be run before the specified package version (excl)."""
    def should_run(config=None):
        version = get_upstream_version(pkg)
        return version and \
            (apt_pkg.version_compare(version, pkg_version) < 0)
    return should_run


def it_has_config(config_key):
    """This audit should be run based on specified config keys."""
    return lambda config: config.get(config_key) is not None


def run(config):
    """Run the configured audits with the specified config.

    :param config: Configuration for the audit
    :type config: Config
    """
    errors = {}
    results = {}
    for name, audit in sorted(_audits.items()):
        result_name = name.replace('_', '-')
        if all(p(config) for p in audit.filters):
            try:
                audit.func(config)
                print("{}: PASS".format(name))
                results[result_name] = {
                    'success': True,
                }
            except AssertionError as e:
                print("{}: FAIL ({})".format(name, e))
                results[result_name] = {
                    'success': False,
                    'message': e,
                }
            except Exception as e:
                print("{}: ERROR ({})".format(name, e))
                errors[name] = e
                results[result_name] = {
                    'success': False,
                    'message': e,
                }
    for name, error in errors.items():
        print("=" * 20)
        print("Error in {}: ".format(name))
        traceback.print_tb(error.__traceback__)
        print()
    return results
