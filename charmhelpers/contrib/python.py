# Copyright 2014-2019 Canonical Limited.
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

from __future__ import absolute_import
from importlib import import_module

_globals = globals()

# deprecated aliases for backwards compatibility
for subpackage in ('debug', 'packages', 'rpdb', 'version'):
    try:
        full_name = 'charmhelpers.fetch.python.{}'.format(subpackage)
        _globals[subpackage] = import_module(full_name)
    except ImportError:
        # not all subpackages may be present if charm-helpers-sync is used
        pass
