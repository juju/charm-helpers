# Copyright 2017 Canonical Ltd
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

import os
import shutil
import json
from mock import patch
from testtools import TestCase
from tempfile import mkdtemp
from charmhelpers.contrib.storage.linux import bcache

test_stats = {
    'bypassed': '128G\n',
    'cache_bypass_hits': '1132623\n',
    'cache_bypass_misses': '0\n',
    'cache_hit_ratio': '64\n',
    'cache_hits': '12177090\n',
    'cache_miss_collisions': '7091\n',
    'cache_misses': '6717011\n',
    'cache_readaheads': '0\n',
}

tmpdir = 'bcache-stats-test.'
cacheset = 'abcde'
cachedev = 'sdfoo'


class BcacheTestCase(TestCase):
    def setUp(self):
        super(BcacheTestCase, self).setUp()
        self.sysfs = sysfs = mkdtemp(prefix=tmpdir)
        self.addCleanup(shutil.rmtree, sysfs)
        p = patch('charmhelpers.contrib.storage.linux.bcache.SYSFS', new=sysfs)
        p.start()
        self.addCleanup(p.stop)
        self.cacheset = '{}/fs/bcache/{}'.format(sysfs, cacheset)
        os.makedirs(self.cacheset)
        self.devcache = '{}/block/{}/bcache'.format(sysfs, cachedev)
        for n in ['register', 'register_quiet']:
            with open('{}/fs/bcache/{}'.format(sysfs, n), 'w') as f:
                f.write('foo')
        for kind in self.cacheset, self.devcache:
            for sub in bcache.stats_intervals:
                intvaldir = '{}/{}'.format(kind, sub)
                os.makedirs(intvaldir)
                for fn, val in test_stats.items():
                    with open(os.path.join(intvaldir, fn), 'w') as f:
                        f.write(val)

    def test_get_bcache_fs(self):
        bcachedirs = bcache.get_bcache_fs()
        assert len(bcachedirs) == 1
        assert next(iter(bcachedirs)).cachepath.endswith('/fs/bcache/abcde')

    @patch('charmhelpers.contrib.storage.linux.bcache.log', lambda *args, **kwargs: None)
    @patch('charmhelpers.contrib.storage.linux.bcache.os.listdir')
    def test_get_bcache_fs_nobcache(self, mock_listdir):
        mock_listdir.side_effect = OSError(
            '[Errno 2] No such file or directory:...')
        bcachedirs = bcache.get_bcache_fs()
        assert bcachedirs == []

    def test_get_stats_global(self):
        out = bcache.get_stats_action(
            'global', 'hour')
        out = json.loads(out)
        assert len(out.keys()) == 1
        k = next(iter(out.keys()))
        assert k.endswith(cacheset)
        assert out[k]['bypassed'] == '128G'

    def test_get_stats_dev(self):
        out = bcache.get_stats_action(
            cachedev, 'hour')
        out = json.loads(out)
        assert len(out.keys()) == 1
        k = next(iter(out.keys()))
        assert k.endswith('sdfoo/bcache')
        assert out[k]['cache_hit_ratio'] == '64'
