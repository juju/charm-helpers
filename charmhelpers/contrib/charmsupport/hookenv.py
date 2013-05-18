"Interactions with the Juju environment"
# Copyright 2012 Canonical Ltd.
#
# Authors:
#  Matthew Wedgwood <matthew.wedgwood@canonical.com>

import os

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
