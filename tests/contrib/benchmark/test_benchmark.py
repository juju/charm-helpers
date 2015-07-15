from functools import partial
from os.path import join
from tempfile import mkdtemp
from shutil import rmtree

import mock
from testtools import TestCase
# import unittest
from charmhelpers.contrib.benchmark import Benchmark, action_set  # noqa
from tests.helpers import patch_open, FakeRelation

TO_PATCH = [
    'in_relation_hook',
    'relation_ids',
    'relation_set',
    'relation_get',
]

FAKE_RELATION = {
    'benchmark:0': {
        'benchmark/0': {
            'hostname': '127.0.0.1',
            'port': '1111',
            'graphite_port': '2222',
            'graphite_endpoint': 'http://localhost:3333',
            'api_port': '4444'
        }
    }
}


class TestBenchmark(TestCase):

    def setUp(self):
        super(TestBenchmark, self).setUp()
        for m in TO_PATCH:
            setattr(self, m, self._patch(m))
        self.fake_relation = FakeRelation(FAKE_RELATION)
        # self.hook_name.return_value = 'benchmark-relation-changed'

        self.relation_get.side_effect = partial(
            self.fake_relation.get, rid="benchmark:0", unit="benchmark/0")
        self.relation_ids.side_effect = self.fake_relation.relation_ids

    def _patch(self, method):
        _m = mock.patch('charmhelpers.contrib.benchmark.' + method)
        m = _m.start()
        self.addCleanup(_m.stop)
        return m

    @mock.patch('os.path.exists')
    @mock.patch('subprocess.check_output')
    def test_benchmark_start(self, check_output, exists):

        exists.return_value = True
        check_output.return_value = "data"

        with patch_open() as (_open, _file):
            self.assertIsNone(Benchmark.start())
            # _open.assert_called_with('/etc/benchmark.conf', 'w')

        COLLECT_PROFILE_DATA = '/usr/local/bin/collect-profile-data'
        exists.assert_any_call(COLLECT_PROFILE_DATA)
        check_output.assert_any_call([COLLECT_PROFILE_DATA])

    def test_benchmark_finish(self):
        with patch_open() as (_open, _file):
            self.assertIsNone(Benchmark.finish())
            # _open.assert_called_with('/etc/benchmark.conf', 'w')

    @mock.patch('charmhelpers.contrib.benchmark.action_set')
    def test_benchmark_set_composite_score(self, action_set):
        self.assertTrue(Benchmark.set_composite_score(15.7, 'hits/sec', 'desc'))
        action_set.assert_called_once_with('meta.composite', {'value': 15.7, 'units': 'hits/sec', 'direction': 'desc'})

    @mock.patch('charmhelpers.contrib.benchmark.find_executable')
    @mock.patch('charmhelpers.contrib.benchmark.subprocess.check_call')
    def test_benchmark_action_set(self, check_call, find_executable):
        find_executable.return_value = "/usr/bin/action-set"
        self.assertTrue(action_set('foo', 'bar'))

        find_executable.assert_called_once_with('action-set')
        check_call.assert_called_once_with(['action-set', 'foo=bar'])

    @mock.patch('charmhelpers.contrib.benchmark.find_executable')
    @mock.patch('charmhelpers.contrib.benchmark.subprocess.check_call')
    def test_benchmark_action_set_dict(self, check_call, find_executable):
        find_executable.return_value = "/usr/bin/action-set"
        self.assertTrue(action_set('baz', {'foo': 1, 'bar': 2}))

        find_executable.assert_called_with('action-set')

        check_call.assert_any_call(['action-set', 'baz.foo=1'])
        check_call.assert_any_call(['action-set', 'baz.bar=2'])

    @mock.patch('charmhelpers.contrib.benchmark.relation_ids')
    @mock.patch('charmhelpers.contrib.benchmark.in_relation_hook')
    def test_benchmark_init(self, in_relation_hook, relation_ids):

        in_relation_hook.return_value = True
        relation_ids.return_value = ['benchmark:0']
        actions = ['asdf', 'foobar']

        tempdir = mkdtemp(prefix=self.__class__.__name__)
        self.addCleanup(rmtree, tempdir)
        conf_path = join(tempdir, "benchmark.conf")
        with mock.patch.object(Benchmark, "BENCHMARK_CONF", conf_path):
            b = Benchmark(actions)

            self.assertIsInstance(b, Benchmark)

            self.assertTrue(self.relation_get.called)
            self.assertTrue(self.relation_set.called)

            relation_ids.assert_called_once_with('benchmark')

            self.relation_set.assert_called_once_with(
                relation_id='benchmark:0',
                relation_settings={'benchmarks': ",".join(actions)}
            )

            conf_contents = open(conf_path).readlines()
            for key, val in iter(FAKE_RELATION['benchmark:0']['benchmark/0'].items()):
                self.assertIn("%s=%s\n" % (key, val), conf_contents)
