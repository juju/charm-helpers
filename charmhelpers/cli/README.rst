==========
Commandant
==========

-----------------------------------------------------
Automatic command-line interfaces to Python functions
-----------------------------------------------------

One of the benefits of ``libvirt`` is the uniformity of the interface: the C  API (as well as the bindings in other languages) is a set of functions that accept parameters that are nearly identical to the command-line arguments.  If you run ``virsh``, you get an interactive command prompt that supports all of the same commands that your shell scripts use as ``virsh`` subcommands.

Command execution and stdio manipulation is the greatest common factor across all development systems in the POSIX environment.  By exposing your functions as commands that manipulate streams of text, you can make life easier for all the Ruby and Erlang and Go programmers in your life.

Goals
=====

* Single decorator to expose a function as a command.
  * now two decorators - one "automatic" and one that allows authors to manipulate the arguments for fine-grained control.(MW)
* Automatic analysis of function signature through ``inspect.getargspec()``
* Command argument parser built automatically with ``argparse``
* Interactive interpreter loop object made with ``Cmd``
* Options to output structured return value data via ``pprint``, ``yaml`` or ``json`` dumps.

Other Important Features that need writing
------------------------------------------

* Help and Usage documentation can be automatically generated, but it will be important to let users override this behaviour
* The decorator should allow specifying further parameters to the parser's add_argument() calls, to specify types or to make arguments behave as boolean flags, etc.
    - Filename arguments are important, as good practice is for functions to accept file objects as parameters.
    - choices arguments help to limit bad input before the function is called
* Some automatic behaviour could make for better defaults, once the user can override them.
    - We could automatically detect arguments that default to False or True, and automatically support --no-foo for foo=True.
    - We could automatically support hyphens as alternates for underscores
    - Arguments defaulting to sequence types could support the ``append`` action.


-----------------------------------------------------
Implementing subcommands
-----------------------------------------------------

(WIP)

So as to avoid dependencies on the cli module, subcommands should be defined separately from their implementations. The recommmendation would be to place definitions into separate modules near the implementations which they expose.

Some examples::

    from charmhelpers.cli import CommandLine
    from charmhelpers.payload import execd
    from charmhelpers.foo import bar

    cli = CommandLine()

    cli.subcommand(execd.execd_run)

    @cli.subcommand_builder("bar", help="Bar baz qux")
    def barcmd_builder(subparser):
        subparser.add_argument('argument1', help="yackety")
        return bar
