charmhelpers.contrib.snap package
=================================

.. automodule:: charmhelpers.contrib.snap
    :members:
    :undoc-members:
    :show-inheritance:

Examples
--------

.. code-block:: python

    snap_install('hello-world', '--classic', '--stable')
    snap_install(['hello-world', 'htop'])

.. code-block:: python

    snap_refresh('hello-world', '--classic', '--stable')
    snap_refresh(['hello-world', 'htop'])

.. code-block:: python

    snap_remove('hello-world')
    snap_remove(['hello-world', 'htop'])

