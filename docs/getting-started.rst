Getting Started
===============

For a video introduction to ``charmhelpers``, check out this
`Charm School session <http://www.youtube.com/watch?v=6kWfLujVwNI>`_. To start
using ``charmhelpers``, proceed with the instructions on the remainder of this
page.

Installing Charm Tools
----------------------

First, follow `these instructions <https://juju.ubuntu.com/docs/tools-charm-tools.html>`_
to install the ``charm-tools`` package for your platform.

Creating a New Charm
--------------------

::

  $ cd ~
  $ mkdirs -p charms/precise
  $ cd charms/precise
  $ charm create -t python mycharm
  INFO: Generating template for mycharm in ./mycharm
  INFO: No mycharm in apt cache; creating an empty charm instead.
  Symlink all hooks to one python source file? [yN] y
  INFO:root:Loading charm helper config from charm-helpers.yaml.
  INFO:root:Checking out lp:charm-helpers to /tmp/tmpPAqUyN/charm-helpers.
  Branched 160 revisions.
  INFO:root:Syncing directory: /tmp/tmpPAqUyN/charm-helpers/charmhelpers/core -> lib/charmhelpers/core.
  INFO:root:Adding missing __init__.py: lib/charmhelpers/__init__.py

Let's see what our new charm looks like::

  $ tree mycharm/
  mycharm/
  ├── charm-helpers.yaml
  ├── config.yaml
  ├── hooks
  │   ├── config-changed -> hooks.py
  │   ├── hooks.py
  │   ├── install -> hooks.py
  │   ├── start -> hooks.py
  │   ├── stop -> hooks.py
  │   └── upgrade-charm -> hooks.py
  ├── icon.svg
  ├── lib
  │   └── charmhelpers
  │       ├── core
  │       │   ├── fstab.py
  │       │   ├── hookenv.py
  │       │   ├── host.py
  │       │   └── __init__.py
  │       └── __init__.py
  ├── metadata.yaml
  ├── README.ex
  ├── revision
  ├── scripts
  │   └── charm_helpers_sync.py
  └── tests
      ├── 00-setup
      └── 10-deploy

  6 directories, 20 files

The ``charmhelpers`` code is bundled in our charm in the ``lib/`` directory.
All of our python code will go in ``hooks/hook.py``. A look at that file reveals
that ``charmhelpers`` has been added to the python path and imported for us::

  $ head mycharm/hooks/hooks.py -n11
  #!/usr/bin/python

  import os
  import sys

  sys.path.insert(0, os.path.join(os.environ['CHARM_DIR'], 'lib'))

  from charmhelpers.core import (
      hookenv,
      host,
  )

Updating Charmhelpers Packages
------------------------------

By default, a new charm installs only the ``charmhelpers.core`` package, but
other packages are available (for a complete list, see the :doc:`api/charmhelpers`).
The installed packages are controlled by the ``charm-helpers.yaml`` file in our charm::

  $ cd mycharm
  $ cat charm-helpers.yaml
  destination: lib/charmhelpers
  branch: lp:charm-helpers
  include:
    - core

Let's update this file to include some more packages::

  $ vim charm-helpers.yaml
  $ cat charm-helpers.yaml
  destination: lib/charmhelpers
  branch: lp:charm-helpers
  include:
    - core
    - contrib.storage
    - fetch

Now we need to download the new packages into our charm::

  $ ./scripts/charm_helpers_sync.py -c charm-helpers.yaml
  INFO:root:Loading charm helper config from charm-helpers.yaml.
  INFO:root:Checking out lp:charm-helpers to /tmp/tmpT38Y87/charm-helpers.
  Branched 160 revisions.
  INFO:root:Syncing directory: /tmp/tmpT38Y87/charm-helpers/charmhelpers/core -> lib/charmhelpers/core.
  INFO:root:Syncing directory: /tmp/tmpT38Y87/charm-helpers/charmhelpers/contrib/storage -> lib/charmhelpers/contrib/storage.
  INFO:root:Adding missing __init__.py: lib/charmhelpers/contrib/__init__.py
  INFO:root:Syncing directory: /tmp/tmpT38Y87/charm-helpers/charmhelpers/fetch -> lib/charmhelpers/fetch.

A look at our charmhelpers directory reveals that the new packages have indeed
been added. We are now free to import and use them in our charm::

  $ tree lib/charmhelpers/
  lib/charmhelpers/
  ├── contrib
  │   ├── __init__.py
  │   └── storage
  │       ├── __init__.py
  │       └── linux
  │           ├── ceph.py
  │           ├── __init__.py
  │           ├── loopback.py
  │           ├── lvm.py
  │           └── utils.py
  ├── core
  │   ├── fstab.py
  │   ├── hookenv.py
  │   ├── host.py
  │   └── __init__.py
  ├── fetch
  │   ├── archiveurl.py
  │   ├── bzrurl.py
  │   └── __init__.py
  └── __init__.py

  5 directories, 15 files

Next Steps
----------

Now that you have access to ``charmhelpers`` in your charm, check out the
:doc:`example-index` or :doc:`api/charmhelpers` to learn about all the great
functionality that ``charmhelpers`` provides.
