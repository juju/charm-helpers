import mock
# import os
# import subprocess
import unittest
# from charmhelpers.core import hookenv
from charmhelpers.contrib.benchmark import Benchmark  # noqa


class TestBenchmark(unittest.TestCase):

    @mock.patch('os.path.exists')
    @mock.patch('subprocess.check_output')
    def test_benchmark_start(self, check_output, exists):

        exists.return_value = True
        check_output.return_value = "data"

        self.assertIsNone(Benchmark().start())

        COLLECT_PROFILE_DATA = '/usr/local/bin/collect-profile-data'
        exists.assert_any_call(COLLECT_PROFILE_DATA)
        check_output.assert_any_call([COLLECT_PROFILE_DATA])

    def test_benchmark_finish(self):
        self.assertIsNone(Benchmark().finish())

    @mock.patch('__builtin__.open')
    @mock.patch('charmhelpers.core.hookenv.relation_get')
    @mock.patch('charmhelpers.core.hookenv.relation_set')
    @mock.patch('charmhelpers.core.hookenv.relation_ids')
    @mock.patch('charmhelpers.core.hookenv.in_relation_hook')
    def test_benchmark_init(self, in_relation_hook, relation_ids, relation_set, relation_get, open_file):

        in_relation_hook.return_value = True
        relation_ids.return_value = ['benchmark:1']
        relation_get.return_value = None
        actions = ['asdf', 'foobar']

        b = Benchmark(actions)

        self.assertIsInstance(b, Benchmark)
        relation_set.assert_called_once_with(
            relation_id='benchmark:1',
            relation_settings={'benchmarks': ",".join(actions)}
        )

        relation_ids.assert_called_once_with('benchmark')
        # relation_set.assert_called
        if in_relation_hook.return_value is True:
            pass
