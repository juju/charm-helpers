Contributing
============

All contributions, both code and documentation, are welcome!

Source
------

The source code is located at https://code.launchpad.net/charm-helpers. To
submit contributions you'll need to create a Launchpad account if you do not
already have one.

To get the code::

  $ bzr branch lp:charm-helpers

To build and run tests::

  $ cd charm-helpers
  $ make

Submitting a Merge Proposal
---------------------------

Run ``make test`` and ensure all tests pass. Then commit your changes and push
them to a personal branch::

  bzr ci -m "Description of your changes"
  bzr push lp:~<launchpad-username>/charm-helpers/my-feature

Note that the branch name ('my-feature' in the above example) can be anything
you choose - preferably something descriptive.

Once your branch is pushed, open it in a web browser, e.g.::

  https://code.launchpad.net/~<launchpad-username>/charm-helpers/my-feature

Find and click on the 'Propose for merging' link, and on the following screen,
click the 'Propose Merge' button.

.. note::

  Do not set a value in the 'Reviewer' field - it will be set automatically.

Open Bugs
---------

If you're looking for something to work on, the open bug/feature list can be
found at https://bugs.launchpad.net/charm-helpers.

Documentation
-------------

If you'd like to contribute to the documentation, please refer to the ``HACKING``
document in the root of the source tree for instructions on building the documentation.

Contributions to the :doc:`example-index` section of the documentation are
especially welcome, and are easy to add. Simply add a new ``.rst`` file under
``charmhelpers/docs/examples``.

Getting Help
------------

If you need help you can find it in ``#juju`` on the Freenode IRC network. Come
talk to us - we're a friendly bunch!
