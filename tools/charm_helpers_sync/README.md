Script for synchronizing charm-helpers into a charm branch.

This script is intended to be used by charm authors during the development
of their charm.  It allows authors to pull in bits of a charm-helpers source
tree and embed directly into their charm, to be deployed with the rest of
their hooks and charm payload.  This script is not intended to be called
by the hooks themselves, but instead by the charm author while they are
hacking on a charm offline.  Consider it a method of compiling specific
revision of a charm-helpers branch into a given charm source tree.

Some goals and benefits to using a sync tool to manage this process:

    - Reduces the burden of manually copying in upstream charm helpers code
      into a charm and helps ensure we can easily keep a specific charm's
      helper code up to date.

    - Allows authors to hack on their own working branch of charm-helpers,
      easily sync into their WIP charm.  Any changes they've made to charm
      helpers can be upstreamed via a merge of their charm-helpers branch
      into lp:charm-helpers, ideally at the same time they are upstreaming
      the charm itself into the charm store.  Separating charm helper
      development from charm development can help reduce cases where charms
      are shipping locally modified helpers.

    - Avoids the need to ship the *entire* charm-helpers source tree with
      a charm.  Authors can selectively pick and choose what subset of helpers
      to include to satisfy the goals of their charm.

Allows specifying a list of dependencies to sync in from a charm-helpers
branch.  Ideally, each charm should describe its requirements in a yaml
config included in the charm, eg `charm-helpers.yaml` (NOTE: Example module
layout as of 12/18/2019):

    $ cd my-charm
    $ cat >charm-helpers.yaml <<END
    repo: https://github.com/juju/charm-helpers
    destination: hooks/helpers
    include:
        - core
        - contrib.openstack
        - contrib.hahelpers:
            - apache
    END

includes may be defined as entire module sub-directories, or as invidual
.py files with in a module sub-directory.

Charm author can then sync in and update helpers as needed.  The following
imports all of `charmhelpers.core` + `charmhelpers.contrib.openstack`, and only
`apache.py` from charmhelpers.contrib.hahelpers:

    $ charm-helpers-sync.py -c charm-helpers.yaml
    $ find hooks/helpers/
    hooks/helpers/
    hooks/helpers/contrib
    hooks/helpers/contrib/hahelpers
    hooks/helpers/contrib/hahelpers/apache.py
    hooks/helpers/contrib/hahelpers/__init__.py
    hooks/helpers/contrib/__init__.py
    hooks/helpers/contrib/openstack
    hooks/helpers/contrib/openstack/templates
    hooks/helpers/contrib/openstack/templates/__init__.py
    hooks/helpers/contrib/openstack/templating.py
    hooks/helpers/contrib/openstack/neutron.py
    hooks/helpers/contrib/openstack/alternatives.py
    hooks/helpers/contrib/openstack/ssh_migrations.py
    hooks/helpers/contrib/openstack/amulet
    hooks/helpers/contrib/openstack/amulet/utils.py
    hooks/helpers/contrib/openstack/amulet/__init__.py
    hooks/helpers/contrib/openstack/amulet/deployment.py
    hooks/helpers/contrib/openstack/utils.py
    hooks/helpers/contrib/openstack/files
    hooks/helpers/contrib/openstack/files/__init__.py
    hooks/helpers/contrib/openstack/__init__.py
    hooks/helpers/contrib/openstack/audits
    hooks/helpers/contrib/openstack/audits/__init__.py
    hooks/helpers/contrib/openstack/audits/openstack_security_guide.py
    hooks/helpers/contrib/openstack/context.py
    hooks/helpers/contrib/openstack/keystone.py
    hooks/helpers/contrib/openstack/policyd.py
    hooks/helpers/contrib/openstack/ip.py
    hooks/helpers/contrib/openstack/exceptions.py
    hooks/helpers/contrib/openstack/vaultlocker.py
    hooks/helpers/contrib/openstack/ha
    hooks/helpers/contrib/openstack/ha/utils.py
    hooks/helpers/contrib/openstack/ha/__init__.py
    hooks/helpers/contrib/openstack/cert_utils.py
    hooks/helpers/__init__.py
    hooks/helpers/core
    hooks/helpers/core/templating.py
    hooks/helpers/core/kernel_factory
    hooks/helpers/core/kernel_factory/__init__.py
    hooks/helpers/core/kernel_factory/ubuntu.py
    hooks/helpers/core/kernel_factory/centos.py
    hooks/helpers/core/files.py
    hooks/helpers/core/hugepage.py
    hooks/helpers/core/__init__.py
    hooks/helpers/core/fstab.py
    hooks/helpers/core/host.py
    hooks/helpers/core/services
    hooks/helpers/core/services/base.py
    hooks/helpers/core/services/__init__.py
    hooks/helpers/core/services/helpers.py
    hooks/helpers/core/hookenv.py
    hooks/helpers/core/host_factory
    hooks/helpers/core/host_factory/__init__.py
    hooks/helpers/core/host_factory/ubuntu.py
    hooks/helpers/core/host_factory/centos.py
    hooks/helpers/core/strutils.py
    hooks/helpers/core/decorators.py
    hooks/helpers/core/sysctl.py
    hooks/helpers/core/unitdata.py
    hooks/helpers/core/kernel.py


Script will create missing `__init__.py`'s to ensure each subdirectory is
importable, assuming the script is run from the charm's top-level directory.

By default, only directories that look like python modules and associated
.py source files will be synced.  If you need to include other files in
the sync (for example, template files), you can add include hints to
your config.  This can be done either on a per-module basis using standard
UNIX filename patterns, eg:

    repo: https://github.com/juju/charm-helpers
    destination: hooks/helpers
    include:
        - core|inc=* # include all extra files from this module.
        - contrib.openstack|inc=*.template # include only .template's
        - contrib.hahelpers:
            - apache|inc=*.cfg # include .cfg files

Or globally for all included assets:

    repo: https://github.com/juju/charm-helpers
    destination: hooks/helpers
    options: inc=*.template,inc=*.cfg # include .templates and .cfgs globally
    include:
        - core
        - contrib.openstack
        - contrib.hahelpers:
            - apache

You may also override configured destination directory:

    $ charm-helpers-sync.py -d hooks/helpers-test \
            -c charm-helpers.yaml

Or not use a config file at all:

    $ charm-helpers-sync.py -r https://github.com/<someone>/charm-helpers \
            -d hooks/helpers core contrib.openstack contrib.hahelpers

or use a specific branch using the @ notation

    $ charm-helpers-sync.py -r https://github.com/<someone>/charm-helpers@branch_name \
            -d hooks/helpers core contrib.openstack contrib.hahelpers

Script will create missing `__init__.py`'s to ensure each subdirectory is
importable, assuming the script is run from the charm's top-level directory.
