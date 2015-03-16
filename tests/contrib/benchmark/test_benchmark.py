import mock
# import os
# import subprocess
import unittest
# from charmhelpers.core import hookenv
from charmhelpers.contrib.benchmark import Benchmark, action_set  # noqa
# from tests.helpers import patch_open, FakeRelation

# FAKE_RELATION = {
#     'benchmark:0': {
#         'benchmark/0': {
#             'hostname': '127.0.0.1',
#             'port': '1111',
#             'graphite_port': '2222',
#             'graphite_endpoint': 'http://localhost:3333',
#             'api_port': '4444'
#         }
#     }
# }
#
# TO_PATCH = [
#     'in_relation_hook',
#     'relation_ids',
#     'relation_set',
#     'relation_get',
# ]


class TestBenchmark(unittest.TestCase):

    # def setUp(self):
    #     super(TestBenchmark, self).setUp()
    #     for m in TO_PATCH:
    #         setattr(self, m, self._patch(m))
    #
    # def _patch(self, method):
    #     _m = mock.patch('charmhelpers.contrib.benchmark.' + method)
    #     m = _m.start()
    #     self.addCleanup(_m.stop)
    #     return m
    #

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

    @mock.patch('__builtin__.open')
    @mock.patch('charmhelpers.contrib.benchmark.relation_get')
    @mock.patch('charmhelpers.contrib.benchmark.relation_set')
    @mock.patch('charmhelpers.contrib.benchmark.relation_ids')
    @mock.patch('charmhelpers.contrib.benchmark.in_relation_hook')
    def test_benchmark_init(self, in_relation_hook, relation_ids, relation_set, relation_get, fopen):

        in_relation_hook.return_value = True
        relation_ids.return_value = ['benchmark:1']
        relation_get.return_value = None
        actions = ['asdf', 'foobar']

        # rel = FakeRelation(IDENTITY_NEW_STYLE_CERTS)
        # self.relation_ids.side_effect = rel.relation_ids
        # self.relation_list.side_effect = rel.relation_units
        # self.relation_get.side_effect = rel.get
        # result = apache_utils.get_cert('test-cn')

        # r = FakeRelation(relation_data=rel)
        # self.relation_get.side_effect = r.get
        # rel_benchmark = self.relation_get('benchmark')

        b = Benchmark(actions)

        # for key in b.required_keys:
        #     relation_get.assert_called_once_with

        self.assertIsInstance(b, Benchmark)
        relation_set.assert_called_once_with(
            relation_id='benchmark:1',
            relation_settings={'benchmarks': ",".join(actions)}
        )

        relation_ids.assert_called_once_with('benchmark')

        # m.assert_called_once_with('/etc/benchmark.conf', 'w')
        # m().write.assert_called_once_with('stuff')

        # with open('/etc/benchmark.conf', 'w') as f:
        #     f.write('stuff')
