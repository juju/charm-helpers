"""Tests for the commandant code that analyzes a function signature to
determine the parameters to argparse."""

from unittest import TestCase
from mock import (
    patch,
    MagicMock,
    ANY,
)
import json
from pprint import pformat
import yaml
import csv

from six import StringIO

from charmhelpers import cli


class SubCommandTest(TestCase):
    """Test creation of subcommands"""

    def setUp(self):
        super(SubCommandTest, self).setUp()
        self.cl = cli.CommandLine()

    @patch('sys.exit')
    def test_subcommand_wrapper(self, _sys_exit):
        """Test function name detection"""
        @self.cl.subcommand()
        def payload():
            "A function that does work."
            pass
        args = self.cl.argument_parser.parse_args(['payload'])
        self.assertEqual(args.func, payload)
        self.assertEqual(_sys_exit.mock_calls, [])

    @patch('sys.exit')
    def test_subcommand_wrapper_bogus_arguments(self, _sys_exit):
        """Test function name detection"""
        @self.cl.subcommand()
        def payload():
            "A function that does work."
            pass
        with self.assertRaises(TypeError):
            with patch("sys.argv", "tests deliberately bad input".split()):
                with patch("sys.stderr"):
                    self.cl.argument_parser.parse_args()
        _sys_exit.assert_called_once_with(2)

    @patch('sys.exit')
    def test_subcommand_wrapper_cmdline_options(self, _sys_exit):
        """Test detection of positional arguments and optional parameters."""
        @self.cl.subcommand()
        def payload(x, y=None):
            "A function that does work."
            return x
        args = self.cl.argument_parser.parse_args(['payload', 'positional', '--y=optional'])
        self.assertEqual(args.func, payload)
        self.assertEqual(args.x, 'positional')
        self.assertEqual(args.y, 'optional')
        self.assertEqual(_sys_exit.mock_calls, [])

    @patch('sys.exit')
    def test_subcommand_builder(self, _sys_exit):
        def noop(z):
            pass

        @self.cl.subcommand_builder('payload', description="A subcommand")
        def payload_command(subparser):
            subparser.add_argument('-z', action='store_true')
            return noop

        args = self.cl.argument_parser.parse_args(['payload', '-z'])
        self.assertEqual(args.func, noop)
        self.assertTrue(args.z)
        self.assertFalse(_sys_exit.called)

    def test_subcommand_builder_bogus_wrapped_args(self):
        with self.assertRaises(TypeError):
            @self.cl.subcommand_builder('payload', description="A subcommand")
            def payload_command(subparser, otherarg):
                pass

    def test_run(self):
        self.bar_called = False

        @self.cl.subcommand()
        def bar(x, y=None, *vargs):
            "A function that does work."
            self.assertEqual(x, 'baz')
            self.assertEqual(y, 'why')
            self.assertEqual(vargs, ('mux', 'zob'))
            self.bar_called = True
            return "qux"

        args = ['chlp', 'bar', '--y', 'why', 'baz', 'mux', 'zob']
        self.cl.formatter = MagicMock()
        with patch("sys.argv", args):
            with patch("charmhelpers.core.unitdata._KV") as _KV:
                self.cl.run()
                assert _KV.flush.called
        self.assertTrue(self.bar_called)
        self.cl.formatter.format_output.assert_called_once_with('qux', ANY)

    def test_no_output(self):
        self.bar_called = False

        @self.cl.subcommand()
        @self.cl.no_output
        def bar(x, y=None, *vargs):
            "A function that does work."
            self.bar_called = True
            return "qux"

        args = ['foo', 'bar', 'baz']
        self.cl.formatter = MagicMock()
        with patch("sys.argv", args):
            self.cl.run()
        self.assertTrue(self.bar_called)
        self.cl.formatter.format_output.assert_called_once_with('', ANY)

    def test_test_command(self):
        self.bar_called = False
        self.bar_result = True

        @self.cl.subcommand()
        @self.cl.test_command
        def bar(x, y=None, *vargs):
            "A function that does work."
            self.bar_called = True
            return self.bar_result

        args = ['foo', 'bar', 'baz']
        self.cl.formatter = MagicMock()
        with patch("sys.argv", args):
            self.cl.run()
        self.assertTrue(self.bar_called)
        self.assertEqual(self.cl.exit_code, 0)
        self.cl.formatter.format_output.assert_called_once_with('', ANY)

        self.bar_result = False
        with patch("sys.argv", args):
            self.cl.run()
        self.assertEqual(self.cl.exit_code, 1)


class OutputFormatterTest(TestCase):
    def setUp(self):
        super(OutputFormatterTest, self).setUp()
        self.expected_formats = (
            "raw",
            "json",
            "py",
            "yaml",
            "csv",
            "tab",
        )
        self.outfile = StringIO()
        self.of = cli.OutputFormatter(outfile=self.outfile)
        self.output_data = {"this": "is", "some": 1, "data": dict()}

    def test_supports_formats(self):
        self.assertEqual(sorted(self.expected_formats),
                         sorted(self.of.supported_formats))

    def test_adds_arguments(self):
        ap = MagicMock()
        arg_group = MagicMock()
        add_arg = MagicMock()
        arg_group.add_argument = add_arg
        ap.add_mutually_exclusive_group.return_value = arg_group
        self.of.add_arguments(ap)

        self.assertTrue(add_arg.called)

        for call_args in add_arg.call_args_list:
            if "--format" in call_args[0]:
                self.assertEqual(sorted(call_args[1]['choices']),
                                 sorted(self.expected_formats))
                self.assertEqual(call_args[1]['default'], 'raw')
                break
        else:
            print(arg_group.call_args_list)
            self.fail("No --format argument was created")

        all_args = [c[0][0] for c in add_arg.call_args_list]
        all_args.extend([c[0][1] for c in add_arg.call_args_list if len(c[0]) > 1])
        for fmt in self.expected_formats:
            self.assertIn("-{}".format(fmt[0]), all_args)
            self.assertIn("--{}".format(fmt), all_args)

    def test_outputs_raw(self):
        self.of.raw(self.output_data)
        self.outfile.seek(0)
        self.assertEqual(self.outfile.read(), str(self.output_data))

    def test_outputs_json(self):
        self.of.json(self.output_data)
        self.outfile.seek(0)
        self.assertEqual(self.outfile.read(), json.dumps(self.output_data))

    def test_outputs_py(self):
        self.of.py(self.output_data)
        self.outfile.seek(0)
        self.assertEqual(self.outfile.read(), pformat(self.output_data) + "\n")

    def test_outputs_yaml(self):
        self.of.yaml(self.output_data)
        self.outfile.seek(0)
        self.assertEqual(self.outfile.read(), yaml.dump(self.output_data))

    def test_outputs_csv(self):
        sample = StringIO()
        writer = csv.writer(sample)
        writer.writerows(self.output_data)
        sample.seek(0)
        self.of.csv(self.output_data)
        self.outfile.seek(0)
        self.assertEqual(self.outfile.read(), sample.read())

    def test_outputs_tab(self):
        sample = StringIO()
        writer = csv.writer(sample, dialect=csv.excel_tab)
        writer.writerows(self.output_data)
        sample.seek(0)
        self.of.tab(self.output_data)
        self.outfile.seek(0)
        self.assertEqual(self.outfile.read(), sample.read())

    def test_formats_output(self):
        for format in self.expected_formats:
            mock_f = MagicMock()
            setattr(self.of, format, mock_f)
            self.of.format_output(self.output_data, format)
            mock_f.assert_called_with(self.output_data)
