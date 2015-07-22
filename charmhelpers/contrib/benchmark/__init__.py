# Copyright 2014-2015 Canonical Limited.
#
# This file is part of charm-helpers.
#
# charm-helpers is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version 3 as
# published by the Free Software Foundation.
#
# charm-helpers is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with charm-helpers.  If not, see <http://www.gnu.org/licenses/>.

import subprocess
import time
import os
from distutils.spawn import find_executable

from charmhelpers.core.hookenv import (
    in_relation_hook,
    relation_ids,
    relation_set,
    relation_get,
)


def action_set(key, val):
    if find_executable('action-set'):
        action_cmd = ['action-set']

        if isinstance(val, dict):
            for k, v in iter(val.items()):
                action_set('%s.%s' % (key, k), v)
            return True

        action_cmd.append('%s=%s' % (key, val))
        subprocess.check_call(action_cmd)
        return True
    return False


class Benchmark():
    """
    Helper class for the `benchmark` interface.

    :param list actions: Define the actions that are also benchmarks

    From inside the benchmark-relation-changed hook, you would
    Benchmark(['memory', 'cpu', 'disk', 'smoke', 'custom'])

    Examples:

        siege = Benchmark(['siege'])
        siege.start()
        [... run siege ...]
        # The higher the score, the better the benchmark
        siege.set_composite_score(16.70, 'trans/sec', 'desc')
        siege.finish()


    """

    BENCHMARK_CONF = '/etc/benchmark.conf'  # Replaced in testing

    required_keys = [
        'hostname',
        'port',
        'graphite_port',
        'graphite_endpoint',
        'api_port'
    ]

    def __init__(self, benchmarks=None):
        if in_relation_hook():
            if benchmarks is not None:
                for rid in sorted(relation_ids('benchmark')):
                    relation_set(relation_id=rid, relation_settings={
                        'benchmarks': ",".join(benchmarks)
                    })

            # Check the relation data
            config = {}
            for key in self.required_keys:
                val = relation_get(key)
                if val is not None:
                    config[key] = val
                else:
                    # We don't have all of the required keys
                    config = {}
                    break

            if len(config):
                with open(self.BENCHMARK_CONF, 'w') as f:
                    for key, val in iter(config.items()):
                        f.write("%s=%s\n" % (key, val))

    @staticmethod
    def start():
        action_set('meta.start', time.strftime('%Y-%m-%dT%H:%M:%SZ'))

        """
        If the collectd charm is also installed, tell it to send a snapshot
        of the current profile data.
        """
        COLLECT_PROFILE_DATA = '/usr/local/bin/collect-profile-data'
        if os.path.exists(COLLECT_PROFILE_DATA):
            subprocess.check_output([COLLECT_PROFILE_DATA])

    @staticmethod
    def finish():
        action_set('meta.stop', time.strftime('%Y-%m-%dT%H:%M:%SZ'))

    @staticmethod
    def set_composite_score(value, units, direction='asc'):
        """
        Set the composite score for a benchmark run. This is a single number
        representative of the benchmark results. This could be the most
        important metric, or an amalgamation of metric scores.
        """
        return action_set(
            "meta.composite",
            {'value': value, 'units': units, 'direction': direction}
        )
