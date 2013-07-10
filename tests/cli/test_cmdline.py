"""Tests for the commandant code that analyzes a function signature to
determine the parameters to argparse."""

from unittest import TestCase
from mock import patch

from charmhelpers import cli


class SubCommandTest(TestCase):
    """Test creation of subcommands"""

    @patch('sys.exit')
    def test_subcommand_wrapper(self, _sys_exit):
        """Test function name detection"""
        cmdline = cli.CommandLine()

        @cmdline.subcommand()
        def payload():
            "A function that does work."
            pass
        args = cmdline.argument_parser.parse_args(['payload'])
        self.assertEqual(args.func, payload)
        self.assertEqual(_sys_exit.mock_calls, [])

    @patch('sys.exit')
    def test_subcommand_wrapper_bogus_arguments(self, _sys_exit):
        """Test function name detection"""
        cmdline = cli.CommandLine()

        @cmdline.subcommand()
        def payload():
            "A function that does work."
            pass
        self.assertRaises(TypeError, cmdline.argument_parser.parse_args,
                          ['deliberately bad input'])
        _sys_exit.assert_called_once_with(2)

    @patch('sys.exit')
    def test_subcommand_wrapper_cmdline_options(self, _sys_exit):
        """Test detection of positional arguments and optional parameters."""
        cmdline = cli.CommandLine()

        @cmdline.subcommand()
        def payload(x, y=None):
            "A function that does work."
            return x
        args = cmdline.argument_parser.parse_args(['payload', 'positional', '--y=optional'])
        self.assertEqual(args.func, payload)
        self.assertEqual(args.x, 'positional')
        self.assertEqual(args.y, 'optional')
        self.assertEqual(_sys_exit.mock_calls, [])

    @patch('sys.exit')
    def test_subcommand_builder(self, _sys_exit):
        cmdline = cli.CommandLine()

        def noop(z):
            pass

        @cmdline.subcommand_builder('payload', description="A subcommand")
        def payload_command(subparser):
            subparser.add_argument('-z', action='store_true')
            return noop

        args = cmdline.argument_parser.parse_args(['payload', '-z'])
        self.assertEqual(args.func, noop)
        self.assertTrue(args.z)
        self.assertFalse(_sys_exit.called)

    def test_subcommand_builder_bogus_wrapped_args(self):
        cmdline = cli.CommandLine()

        with self.assertRaises(TypeError):
            @cmdline.subcommand_builder('payload', description="A subcommand")
            def payload_command(subparser, otherarg):
                pass
