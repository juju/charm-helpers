Interacting with Charm Configuration
====================================

The :func:`charmhelpers.core.hookenv.config`, when called with no arguments,
returns a :class:`charmhelpers.core.hookenv.Config` instance - a dictionary
representation of a charm's ``config.yaml`` file. This object can
be used to:

* get a charm's current config values
* check if a config value has changed since the last hook invocation
* view the previous value of a changed config item
* save arbitrary key/value data for use in a later hook

For the following examples we'll assume our charm has a config.yaml file that
looks like this::

  options:
    app-name:
      type: string
      default: "My App"
      description: "Name of your app."


Getting charm config values
---------------------------

::

  # hooks/hooks.py

  from charmhelpers.core import hookenv

  hooks = hookenv.Hooks()

  @hooks.hook('install')
  def install():
      config = hookenv.config()

      assert config['app-name'] == 'My App'

Checking if a config value has changed
--------------------------------------

Let's say the user changes the ``app-name`` config value at runtime by
executing the following juju command::

  juju set mycharm app-name="My New App"

which triggers a ``config-changed`` hook::

  # hooks/hooks.py

  from charmhelpers.core import hookenv

  hooks = hookenv.Hooks()

  @hooks.hook('config-changed')
  def config_changed():
      config = hookenv.config()

      assert config.changed('app-name')
      assert config['app-name'] == 'My New App'
      assert config.previous('app-name') == 'My App'

Saving arbitrary key/value data
-------------------------------

The :class:`Config <charmhelpers.core.hookenv.Config>` object maybe also be
used to store arbitrary data that you want to persist across hook
invocations::

  # hooks/hooks.py

  from charmhelpers.core import hookenv

  hooks = hookenv.Hooks()

  @hooks.hook('install')
  def install():
      config = hookenv.config()

      config['mykey'] = 'myval'

  @hooks.hook('config-changed')
  def config_changed():
      config = hookenv.config()

      assert config['mykey'] == 'myval'
