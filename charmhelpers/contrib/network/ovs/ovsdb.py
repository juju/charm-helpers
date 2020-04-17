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
import json
import uuid

from . import utils


class SimpleOVSDB(object):
    """Simple interface to OVSDB through the use of command line tools.

    OVS and OVN is managed through a set of databases.  These databases have
    similar command line tools to manage them.  We make use of the similarity
    to provide a generic class that can be used to manage them.

    The OpenvSwitch project does provide a Python API, but on the surface it
    appears to be a bit too involved for our simple use case.

    Examples:
    chassis = SimpleOVSDB('ovn-sbctl', 'chassis')
    for chs in chassis:
        print(chs)

    bridges = SimpleOVSDB('ovs-vsctl', 'bridge')
    for br in bridges:
        if br['name'] == 'br-test':
            bridges.set(br['uuid'], 'external_ids:charm', 'managed')
    """

    def __init__(self, tool, table):
        """SimpleOVSDB constructor

        :param tool: Which tool with database commands to operate on.
                     Usually one of `ovs-vsctl`, `ovn-nbctl`, `ovn-sbctl`
        :type tool: str
        :param table: Which table to operate on
        :type table: str
        """
        if tool not in ('ovs-vsctl', 'ovn-nbctl', 'ovn-sbctl'):
            raise RuntimeError(
                "tool must be one of 'ovs-vsctl', 'ovn-nbctl', 'ovn-sbctl'")
        self.tool = tool
        self.tbl = table

    def _find_tbl(self, condition=None):
        """Run and parse output of OVSDB `find` command.

        :param condition: An optional RFC 7047 5.1 match condition
        :type condition: Optional[str]
        :returns: Dictionary with data
        :rtype: Iterator[Dict[str, ANY]]
        """
        # When using json formatted output to OVS commands Internal OVSDB
        # notation may occur that require further deserializing.
        # Reference: https://tools.ietf.org/html/rfc7047#section-5.1
        ovs_type_cb_map = {
            'uuid': uuid.UUID,
            # FIXME sets also appear to sometimes contain type/value tuples
            'set': list,
            'map': dict,
        }
        cmd = [self.tool, '-f', 'json', 'find', self.tbl]
        if condition:
            cmd.append(condition)
        output = utils._run(*cmd)
        data = json.loads(output)
        for row in data['data']:
            values = []
            for col in row:
                if isinstance(col, list):
                    f = ovs_type_cb_map.get(col[0], str)
                    values.append(f(col[1]))
                else:
                    values.append(col)
            yield dict(zip(data['headings'], values))

    def __iter__(self):
        return self._find_tbl()

    def clear(self, rec, col):
        utils._run(self.tool, 'clear', self.tbl, rec, col)

    def find(self, condition):
        return self._find_tbl(condition=condition)

    def remove(self, rec, col, value):
        utils._run(self.tool, 'remove', self.tbl, rec, col, value)

    def set(self, rec, col, value):
        utils._run(self.tool, 'set', self.tbl, rec, '{}={}'.format(col, value))
