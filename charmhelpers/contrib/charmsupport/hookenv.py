"Interactions with the Juju environment"
# Copyright 2012 Canonical Ltd.
#
# Authors:
#  Matthew Wedgwood <matthew.wedgwood@canonical.com>

import os
import json
import yaml
import subprocess
import UserDict

CRITICAL = "CRITICAL"
ERROR = "ERROR"
WARNING = "WARNING"
INFO = "INFO"
DEBUG = "DEBUG"
MARKER = object()


def log(message, level=None):
    "Write a message to the juju log"
    command = ['juju-log']
    if level:
        command += ['-l', level]
    command += [message]
    subprocess.call(command)


class Serializable(UserDict.IterableUserDict):
    "Wrapper, an object that can be serialized to yaml or json"

    def __init__(self, obj):
        # wrap the object
        UserDict.IterableUserDict.__init__(self)
        self.data = obj

    def __getattr__(self, attr):
        # See if this object has attribute.
        if attr in ("json", "yaml", "data"):
            return self.__dict__[attr]
        # Check for attribute in wrapped object.
        got = getattr(self.data, attr, MARKER)
        if got is not MARKER:
            return got
        # Proxy to the wrapped object via dict interface.
        try:
            return self.data[attr]
        except KeyError:
            raise AttributeError(attr)

    def json(self):
        "Serialize the object to json"
        return json.dumps(self.data)

    def yaml(self):
        "Serialize the object to yaml"
        return yaml.dump(self.data)


def execution_environment():
    """A convenient bundling of the current execution context"""
    context = {}
    context['conf'] = config()
    context['unit'] = local_unit()
    context['rel'] = relations_of_type()
    context['env'] = os.environ
    return context


def in_relation_hook():
    "Determine whether we're running in a relation hook"
    return 'JUJU_RELATION' in os.environ


def relation_type():
    "The scope for the current relation hook"
    return os.environ.get('JUJU_RELATION', None)


def relation_id():
    "The relation ID for the current relation hook"
    return os.environ.get('JUJU_RELATION_ID', None)


def local_unit():
    "Local unit ID"
    return os.environ['JUJU_UNIT_NAME']


def remote_unit():
    "The remote unit for the current relation hook"
    return os.environ['JUJU_REMOTE_UNIT']


def config(scope=None):
    "Juju charm configuration"
    config_cmd_line = ['config-get']
    if scope is not None:
        config_cmd_line.append(scope)
    config_cmd_line.append('--format=json')
    try:
        config_data = json.loads(subprocess.check_output(config_cmd_line))
    except (ValueError, OSError, subprocess.CalledProcessError) as err:
        log(str(err), level=ERROR)
        raise
    return Serializable(config_data)


def relation_get(attribute=None, unit=None, rid=None):
    _args = ['relation-get', '--format=json']
    if rid:
        _args.append('-r')
        _args.append(rid)
    if attribute is not None:
        _args.append(attribute)
    else:
        _args.append('-')
    if unit:
        _args.append(unit)
    return json.loads(subprocess.check_output(_args))


def relation_set(relation_id=None, **kwargs):
    relation_cmd_line = ['relation-set']
    if relation_id is not None:
        relation_cmd_line.extend(('-r', relation_id))
    for k, v in kwargs.items():
        relation_cmd_line.append('{}={}'.format(k, v))
    subprocess.check_call(relation_cmd_line)


def relation_ids(reltype=None):
    "A list of relation_ids"
    reltype = reltype or relation_type()
    relid_cmd_line = ['relation-ids', '--format=json']
    if reltype is not None:
        relid_cmd_line.append(reltype)
        return json.loads(subprocess.check_output(relid_cmd_line))
    else:
        return []


def related_units(relid=None):
    "A list of related units"
    relid = relid or relation_id()
    units_cmd_line = ['relation-list', '--format=json']
    if relid is not None:
        units_cmd_line.extend(('-r', relid))
    result = json.loads(subprocess.check_output(units_cmd_line))
    if not result:
        return []
    return result


def relation_for_unit(unit=None, rid=None):
    "Get the json represenation of a unit's relation"
    unit = unit or remote_unit()
    relation = relation_get(unit=unit, rid=rid)
    for key in relation:
        if key.endswith('-list'):
            relation[key] = relation[key].split()
    relation['__unit__'] = unit
    return Serializable(relation)


def relations_for_id(relid=None):
    "Get relations of a specific relation ID"
    relation_data = []
    relid = relid or relation_id()
    for unit in related_units(relid):
        unit_data = relation_for_unit(unit, relid)
        unit_data['__relid__'] = relid
        relation_data.append(unit_data)
    return relation_data


def relations_of_type(reltype=None):
    "Get relations of a specific type"
    relation_data = []
    reltype = reltype or relation_type()
    if reltype is None:
        return []
    for relid in relation_ids(reltype):
        for relation in relations_for_id(relid):
            relation['__relid__'] = relid
            relation_data.append(relation)
    return relation_data


class UnregisteredHookError(Exception):
    pass


class Hooks(object):
    def __init__(self):
        super(Hooks, self).__init__()
        self._hooks = {}

    def register(self, name, function):
        self._hooks[name] = function

    def execute(self, args):
        hook_name = os.path.basename(args[0])
        if hook_name in self._hooks:
            self._hooks[hook_name]()
        else:
            raise UnregisteredHookError(hook_name)

    def hook(self, *hook_names):
        def wrapper(decorated):
            for hook_name in hook_names:
                self.register(hook_name, decorated)
            else:
                self.register(decorated.__name__, decorated)
            return decorated
        return wrapper
