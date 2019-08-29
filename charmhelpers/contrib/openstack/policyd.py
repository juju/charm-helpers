# Copyright 2019 Canonical Ltd
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
import contextlib
import os
import six
import shutil
import yaml
import zipfile

import charmhelpers.core.hookenv as hookenv
import charmhelpers.core.host as ch_host

# Policy.d helper functions.
#
# The /etc/<service-name>/policy.d/ directory, for OpenStack services can
# contain YAML or JSON files to override the default policies configured in a
# service.  These helpers are used to load, validate, and write YAML files to
# the policy.d directory

# The config.yaml for the charm should contain the following for the config
# option:

"""
  use-policyd-override:
    type: boolean
    default: False
    description: |
      If True then use the resource file named 'policyd-override' to install
      override yaml files in the service's policy.d directory.  The resource
      file should be a zip file containing at least one yaml file with a .yaml
      or .yml extension.  If False then remove the overrides.
"""

# The metadata.yaml for the charm should contain the following:
"""
resources:
  policyd-override:
    type: file
    filename: policyd-override.zip
    description: The policy.d overrides file
"""

# The README for the charm should contain the following:
"""
Policy Overrides
----------------

This service allows for policy overrides using the `policy.d` directory.  This
is an **advanced** feature and the policies that the service supports should be
clearly and unambiguously understood before trying to override, or add to, the
default policies that the service uses.

The charm also has some policy defaults.  They should also be understood before
being overridden.  It is possible to break the system (for tenants and other
services) if policies are incorrectly applied to the service.

Policy overrides are YAML files that contain rules that will add to, or
override, existing policy rules in the service.  The `policy.d` directory is
a place to put the YAML override files.  This charm owns the
`/etc/keystone/policy.d` directory, and as such, any manual changes to it will
be overwritten on charm upgrades.

Policy overrides are provided to the charm using a resource file called
`policyd-override`.  This is attached to the charm using (for example):

    juju attach-resource <charm-name> policyd-override=<some-file>

The `<charm-name>` is the name that this charm is deployed as, with
`<some-file>` being the resource file containing the policy overrides.

The format of the resource file is a ZIP file (.zip extension) containing at
least one YAML file with an extension of `.yaml` or `.yml`.  Note that any
directories in the ZIP file are ignored; all of the files are flattened into
a single directory.  There must not be any duplicated filenames; this will
cause an error and nothing in the resource file will be applied.

To enable the policy overrides the config option `use-policyd-override` must be
set to `True`.

When `use-policyd-override` is `True` the status line of the charm will be
prefixed with `PO:` indicating that policies have been overridden.  If the
installation of the policy override YAML files failed for any reason then the
status line will be prefixed with `PO (broken):`.  The log file for the charm
will indicate the reason.  No policy override files are installed if the `PO
(broken):` is shown.  The status line indicates that the overrides are broken,
not that the policy for the service has failed - they will be the defaults for
the charm and service.

If the policy overrides did not install then *either* attach a new, corrected,
resource file *or* disable the policy overrides by setting
`use-policyd-override` to False.

Policy overrides on one service may affect the functionality of another
service. Therefore, it may be necessary to provide policy overrides for
multiple service charms to achieve a consistent set of policies across the
OpenStack system.  The charms for the other services that may need overrides
should be checked to ensure that they support overrides before proceeding.
"""

YAML_EXTS = ['.yaml', '.yml']
POLICYD_RESOURCE_NAME = "policyd-override"
POLICYD_CONFIG_NAME = "use-policyd-override"
POLICYD_SUCCESS_FILENAME = "policyd-override-success"
POLICYD_LOG_LEVEL_DEFAULT = hookenv.INFO


class BadPolicyZipFile(Exception):

    def __init__(self, log_message):
        self.log_message = log_message


class BadPolicyYamlFile(Exception):

    def __init__(self, log_message):
        self.log_message = log_message


def is_policyd_override_valid_on_this_release(openstack_release):
    """Check that the charm is running on at least Ubuntu bionic, and at
    least the queens release.

    :param openstack_release: the release codename that is installed.
    :type openstack_release: str
    :returns: True if okay
    :rtype: bool
    """
    ubuntu_release = ch_host.lsb_release()['DISTRIB_CODENAME'].lower()
    # TODO(ajkavanagh) circular import!  This is because the status message
    # generation code in utils has to call into this module, but this function
    # needs the CompareOpenStackReleases() function.  The only way to solve
    # this is either to put ALL of this module into utils, or refactor one or
    # other of the CompareOpenStackReleases or status message generation code
    # into a 3rd module.
    import charmhelpers.contrib.openstack.utils as ch_utils
    return (ch_host.CompareHostReleases(ubuntu_release) >= 'bionic' and
            ch_utils.CompareOpenStackReleases(openstack_release) >= 'queens')


def maybe_do_policyd_overrides(openstack_release,
                               service,
                               blacklist_paths=None,
                               blacklist_keys=None,
                               modify_function=None,
                               restart_handler=None):
    """If the config option is set, get the resource file and process it to
    enable the policy.d overrides for the service passed.

    The param `openstack_release` is required as the policyd overrides feature
    is only supported on openstack_release "queens" or later, and on ubuntu
    "bionic" or later.  Prior to these versions, this feature is a NOP.

    The optional modify_function is a function that accepts a python dictionary
    and has an opportunity to modify the yaml (as a python object) prior to it
    being written to the disk.

    The param blacklist_paths are paths (that are in the service's policy.d
    directory that should not be touched).

    The param blacklist_keys are keys that must not appear in the yaml file.
    If they do, then the whole policy.d file fails.

    The yaml file extracted from the resource_file (which is a zipped file) has
    its file path reconstructed.  This, also, must not match any path in the
    black list.

    The param restart_handler is an optional Callable that is called to perform
    the service restart if the policy.d file is changed.  This should normally
    be None as oslo.policy automatically picks up changes in the policy.d
    directory.  However, for any services where this is buggy then a
    restart_handler can be used to force the policy.d files to be read.

    :param openstack_release: The openstack release that is installed.
    :type openstack_release: str
    :param service: the service name to construct the policy.d directory for.
    :type service: str
    :param blacklist_paths: optional list of paths to leave alone
    :type blacklist_paths: Union[None, List[str]]
    :param blacklist_keys: optional list of keys that mustn't appear in the
                           yaml file's
    :type blacklist_keys: Union[None, List[str]]
    :param modify_function: Optional function that can modify the yaml
                            document.
    :type modify_function: Union[None,
                                 Callable[[Dict[str, str]], Dict[str,str]]]
    :param restart_handler: The function to call if the service should be
                            restarted.
    :type restart_handler: Union[None, Callable[]]
    """
    config = hookenv.config()
    try:
        if not config.get(POLICYD_CONFIG_NAME, False):
            return
    except Exception:
        return
    if not is_policyd_override_valid_on_this_release(openstack_release):
        return
    # from now on it should succeed; if it doesn't then status line will show
    # broken.
    resource_filename = get_policy_resource_filename()
    restart = process_policy_resource_file(
        resource_filename, service, blacklist_paths, blacklist_keys,
        modify_function)
    if restart and restart_handler is not None and callable(restart_handler):
        restart_handler()


def maybe_do_policyd_overrides_on_config_changed(openstack_release,
                                                 service,
                                                 blacklist_paths=None,
                                                 blacklist_keys=None,
                                                 modify_function=None,
                                                 restart_handler=None):
    """This function is designed to be called from the config changed hook
    handler.  It will only perform the policyd overrides if the config is True
    and the success file doesn't exist.  Otherwise, it does nothing as the
    resource file has already been processed.

    See maybe_do_policyd_overrides() for more details on the params.

    :param openstack_release: The openstack release that is installed.
    :type openstack_release: str
    :param service: the service name to construct the policy.d directory for.
    :type service: str
    :param blacklist_paths: optional list of paths to leave alone
    :type blacklist_paths: Union[None, List[str]]
    :param blacklist_keys: optional list of keys that mustn't appear in the
                           yaml file's
    :type blacklist_keys: Union[None, List[str]]
    :param modify_function: Optional function that can modify the yaml
                            document.
    :type modify_function: Union[None,
                                 Callable[[Dict[str, str]], Dict[str,str]]]
    :param restart_handler: The function to call if the service should be
                            restarted.
    :type restart_handler: Union[None, Callable[]]
    """
    config = hookenv.config()
    try:
        if not config.get(POLICYD_CONFIG_NAME, False):
            return
    except Exception:
        return
    if not is_policyd_override_valid_on_this_release(openstack_release):
        return
    # if the policyd overrides have been performed just return
    if os.path.isfile(_policy_success_file()):
        return
    maybe_do_policyd_overrides(
        service, blacklist_paths, blacklist_keys, modify_function,
        restart_handler)


def get_policy_resource_filename():
    """Function to extract the policy resource filename

    :returns: The filename of the resource, if set, otherwise, if an error
               occurs, then None is returned.
    :rtype: Union[str, None]
    """
    try:
        return hookenv.resource_get(POLICYD_RESOURCE_NAME)
    except Exception:
        return None


@contextlib.contextmanager
def open_and_filter_yaml_files(filepath):
    """Validate that the filepath provided is a zip file and contains at least
    one (.yaml|.yml) file, and that the files are not duplicated when the zip
    file is flattened.  Note that the yaml files are not checked.  This is the
    first stage in validating the policy zipfile; individual yaml files are not
    checked for validity or black listed keys.

    An example of use is:

        with open_and_filter_yaml_files(some_path) as zfp, g:
            for zipinfo in g:
                # do something with zipinfo ...

    :param filepath: a filepath object that can be opened by zipfile
    :type filepath: Union[AnyStr, os.PathLike[AntStr]]
    :returns: (zfp handle,
               a generator of the (name, filename, ZipInfo object) tuples) as a
               tuple.
    :rtype: ContextManager[(zipfile.ZipFile,
                            Generator[(name, str, str, zipfile.ZipInfo)])]
    :raises: zipfile.BadZipFile
    :raises: BadPolicyZipFile if duplicated yaml or missing
    :raises: IOError if the filepath is not found
    """
    with zipfile.ZipFile(filepath, 'r') as zfp:
        # first pass through; check for duplicates and at least one yaml file.
        names = collections.defaultdict(int)
        for name, _, _ in _yield_yamlfiles(zfp):
            names[name] += 1
        # There must be at least 1 yaml file.
        if not names:
            raise BadPolicyZipFile("contains no yaml files with {} extensions."
                                   .format(", ".join(YAML_EXTS)))
        # There must be no duplicates
        duplicates = [n for n, c in names if c > 1]
        if duplicates:
            raise BadPolicyZipFile("{} have duplicates in the zip file."
                                   .format(", ".join(duplicates)))
        # Finally, let's yield the generator
        yield (zfp, _yield_yamlfiles(zfp))


def _yield_yamlfiles(zipfile):
    """Helper to get a yaml file (according to YAML_EXTS extensions) and the
    infolist item from a zipfile.

    :param zipfile: the zipfile to read zipinfo items from
    :type zipfile: zipfile.ZipFile
    :returns: generator of (name, filename, info item) for each self-identified
              yaml file.
    :rtype: Generator[(str, str, zipfile.ZipInfo)]
    """
    for infolist_item in zipfile.infolist():
        if infolist_item.is_dir():
            continue
        _, name_ext = os.path.split(zipfile.filename)
        name, ext = os.path.splitext(name_ext)
        ext = ext.lower()
        if ext and ext in YAML_EXTS:
            yield name, name_ext, infolist_item


def read_and_validate_yaml(stream, blacklist_keys=None):
    """Read, validate and return the (first) yaml document from the stream.

    The stream is read, and checked for a yaml file.  The the top-level keys
    are checked against the blacklist_keys provided.  If there are problems
    then an Exception is raised.  Otherwise the yaml document is returned as a
    Python object that can be dumped back as a yaml file on the system.

    The yaml file must only consist of a str:str mapping, and if not then the
    yaml file is rejected.

    :param stream: the file object to read the yaml from
    :type stream: Union[AnyStr, IO[AnyStr]]
    :param blacklist_keys: Any keys, which if in the yaml file, should cause
        and error.
    :type blacklisted_keys: Union[None, List[str]]
    :returns: the yaml file as a python document
    :rtype: Dict[str, str]
    :raises: yaml.YAMLError if there is a problem with the document
    :raises: BadPolicyYamlFile if file doesn't look right or there are
             blacklisted keys in the file.
    """
    blacklist_keys = blacklist_keys or []
    doc = yaml.safe_load(stream)
    if not isinstance(doc, dict):
        raise BadPolicyYamlFile("doesn't look like a policy file?")
    keys = set(doc.keys())
    blacklisted_keys_present = keys.union(blacklist_keys)
    if blacklisted_keys_present:
        raise BadPolicyYamlFile("blacklisted keys {} present."
                                .format(", ".join(blacklisted_keys_present)))
    if not all(isinstance(k, six.string_types) for k in keys):
        raise BadPolicyYamlFile("keys in yaml aren't all strings?")
    # check that the dictionary looks like a mapping of str to str
    if not all(isinstance(v, six.string_types) for v in doc.values()):
        raise BadPolicyYamlFile("values in yaml aren't all strings?")
    return doc


def policyd_dir_for(service):
    """Return the policy directory for the named service.

    This assumes the default name of "policy.d" which is kept across all
    charms.

    :param service: str
    :returns: the policy.d override directory.
    :rtype: os.PathLike[str]
    """
    return os.path.join("etc", service, "policy.d")


def clean_policyd_dir_for(service, keep_paths=None):
    """Clean out the policyd directory except for items that should be kept.

    The keep_paths, if used, should be set to the full path of the files that
    should be kept in the policyd directory for the service.  Note that the
    service name is passed in, and then the policyd_dir_for() function is used.
    This is so that a coding error doesn't result in a sudden deletion of the
    charm (say).

    :param service: the service name to use to construct the policy.d dir.
    :type service: str
    :param keep_paths: optional list of paths to not delete.
    :type keep_paths: Union[None, List[str]]
    """
    keep_paths = keep_paths or []
    for direntry in os.scandir(policyd_dir_for(service)):
        # see if the path should be kept.
        if direntry.path in keep_paths:
            continue
        # we remove any directories; it's ours and there shouldn't be any
        if direntry.is_dir():
            shutil.rmtree(direntry.path)
        else:
            os.remove(direntry.path)


def path_for_policy_file(service, name):
    """Return the full path for a policy.d file that will be written to the
    service's policy.d directory.

    It is constructed using policyd_dir_for(), the name and the ".yaml"
    extension.

    :param service: the service name
    :type service: str
    :param name: the name for the policy override
    :type name: str
    :returns: the full path name for the file
    :rtype: os.PathLike[str]
    """
    return os.path.join(policyd_dir_for(service), name + ".yaml")


def _policy_success_file():
    """Return the file name for a successful drop of policy.d overrides

    :returns: the path name for the file.
    :rtype: str
    """
    return os.path.join(hookenv.charm_dir(), POLICYD_SUCCESS_FILENAME)


def remove_policy_success_file():
    """Remove the file that indicates successful policyd override."""
    try:
        os.remove(_policy_success_file())
    except Exception:
        pass


def policyd_status_message_prefix():
    """Return the prefix str for the status line.

    "PO:" indicating that the policy overrides are in place, or "PO (broken):"
    if the policy is supposed to be working but there is no success file.

    :returns: the prefix
    :rtype: str
    """
    if os.path.isfile(_policy_success_file()):
        return "PO:"
    return "PO (broken):"


def process_policy_resource_file(resource_file,
                                 service,
                                 blacklist_paths=None,
                                 blacklist_keys=None,
                                 modify_function=None):
    """Process the resource file (which should contain at least one yaml file)
    and write those files to the service's policy.d directory.

    The optional modify_function is a function that accepts a python dictionary
    and has an opportunity to modify the yaml (as a python object) prior to it
    being written to the disk.

    The param blacklist_paths are paths (that are in the service's policy.d
    directory that should not be touched).

    The param blacklist_keys are keys that must not appear in the yaml file.
    If they do, then the whole policy.d file fails.

    The yaml file extracted from the resource_file (which is a zipped file) has
    its file path reconstructed.  This, also, must not match any path in the
    black list.

    If any error occurs, then the policy.d directory is cleared, the error is
    written to the log, and the status line will eventually show as failed.

    :param resource_file: The zipped file to open and extract yaml files form.
    :type resource_file: Union[AnyStr, os.PathLike[AnyStr]]
    :param service: the service name to construct the policy.d directory for.
    :type service: str
    :param blacklist_paths: optional list of paths to leave alone
    :type blacklist_paths: Union[None, List[str]]
    :param blacklist_keys: optional list of keys that mustn't appear in the
                           yaml file's
    :type blacklist_keys: Union[None, List[str]]
    :param modify_function: Optional function that can modify the yaml
                            document.
    :type modify_function: Union[None,
                                 Callable[[Dict[str, str]], Dict[str,str]]]
    :returns: True if the processing was successful, False if not.
    :rtype: boolean
    """
    completed = False
    try:
        with open_and_filter_yaml_files(resource_file) as (zfp, gen):
            # first clear out the policy.d directory and clear success
            remove_policy_success_file()
            clean_policyd_dir_for(service, blacklist_paths)
            for name, filename, zipinfo in gen:
                # construct a name for the output file.
                yaml_filename = path_for_policy_file(service, name)
                if yaml_filename in blacklist_paths:
                    raise BadPolicyZipFile("policy.d name {} is blacklisted"
                                           .format(yaml_filename))
                with zfp.open(gen) as fp:
                    yaml_doc = read_and_validate_yaml(fp, blacklist_keys)
                if modify_function is not None and callable(modify_function):
                    yaml_doc = modify_function(yaml_doc)
                with open(yaml_filename, "wt") as f:
                    yaml.dump(yaml_doc, f)
        # Every thing worked, so we mark up a success.
        completed = True
    except (zipfile.BadZipFile, BadPolicyZipFile, BadPolicyYamlFile) as e:
        hookenv.log("Processing {} failed: {}".format(resource_file, str(e)),
                    level=POLICYD_LOG_LEVEL_DEFAULT)
    except IOError as e:
        # technically this shouldn't happen; it would be a programming error as
        # the filename comes from Juju and thus, should exist.
        hookenv.log(
            "File {} failed with IOError.  This really shouldn't happen"
            " -- error: {}".format(str(e)),
            level=POLICYD_LOG_LEVEL_DEFAULT)
    finally:
        if not completed:
            hookenv.log("Processing {} failed: cleaning policy.d directory",
                        level=POLICYD_LOG_LEVEL_DEFAULT)
            clean_policyd_dir_for(service, blacklist_paths)
        else:
            # touch the success filename
            hookenv.log("policy.d overrides installed.",
                        level=POLICYD_LOG_LEVEL_DEFAULT)
            open(_policy_success_file(), "w").close()
        return completed
