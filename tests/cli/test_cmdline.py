"""Tests for the commandant code that analyzes a function signature to
determine the parameters to argparse."""

from unittest import TestCase
from mock import (
    patch,
    MagicMock,
    call,
)

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
            self.cl.argument_parser.parse_args('deliberately bad input')
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
        self.outfile = MagicMock()
        self.of = cli.OutputFormatter(outfile=self.outfile)

    def test_supports_formats(self):
        self.assertItemsEqual(self.expected_formats, self.of.supported_formats)

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
                self.assertItemsEqual(call_args[1]['choices'], self.expected_formats)
                self.assertEqual(call_args[1]['default'], 'raw')
                break
        else:
            print arg_group.call_args_list
            self.fail("No --format argument was created")

        all_args = [c[0][0] for c in add_arg.call_args_list]
        all_args.extend([c[0][1] for c in add_arg.call_args_list if len(c[0]) > 1])
        for fmt in self.expected_formats:
            self.assertIn("-{}".format(fmt[0]), all_args)
            self.assertIn("--{}".format(fmt), all_args)

    def test_outputs_raw(self):
        pass

    def test_outputs_json(self):
        pass

    def test_outputs_py(self):
        pass

    def test_outputs_yaml(self):
        pass

    def test_outputs_csv(self):
        pass

    def test_outputs_tab(self):
        pass
