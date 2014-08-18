Managing Charms with the Services Framework
===========================================

Traditional charm authoring is focused on implementing hooks.  That is,
the charm author is thinking in terms of "What hook am I handling; what
does this hook need to do?"  However, in most cases, the real question
should be "Do I have the information I need to configure and start this
piece of software and, if so, what are the steps for doing so?"  The
services framework tries to bring the focus to the data and the
setup tasks, in the most declarative way possible.


Hooks as Data Sources for Service Definitions
---------------------------------------------

While the ``install``, ``start``, and ``stop`` hooks clearly represent
state transitions, all of the other hooks are really notifications of
changes in data from external sources, such as config data values in
the case of ``config-changed`` or relation data for any of the
``*-relation-*`` hooks.  Moreover, many charms that rely on external
data from config options or relations find themselves needing some
piece of external data before they can even configure and start anything,
and so the ``start`` hook loses its semantic usefulness.

If data is required from multiple sources, it even becomes impossible to
know which hook will be executing when all required data is available.
(E.g., which relation will be the last to execute; will the required
config option be set before or after all of the relations are available?)
One common solution to this problem is to create "flag files" to track
whether a given bit of data has been observed, but this can get cluttered
quickly and is difficult to understand what conditions lead to which actions.

When using the services framework, all hooks other than ``install``
are handled by a single call to :meth:`manager.manage() <charmhelpers.core.services.base.ServiceManager.manage>`.
This can be done with symlinks, or by having a ``definitions.py`` file
containing the service defintions, and every hook can be reduced to::

  #!/bin/env python
  from charmhelpers.core.services import ServiceManager
  from definitions import service_definitions
  ServiceManager(service_definitions).manage()

So, what magic goes into ``definitions.py``?


Service Definitions Overview
----------------------------

The format of service definitions are fully documented in
:class:`~charmhelpers.core.services.base.ServiceManager`, but most commonly
will consist of one or more dictionaries containing four items: the name of
a service being managed, the list of data contexts required before the service
can be configured and started, the list of actions to take when the data
requirements are satisfied, and list of ports to open.  The service name
generally maps to an Upstart job, the required data contexts are ``dict``
or ``dict``-like structures that contain the data once available (usually
subclasses of :class:`~charmhelpers.core.services.helpers.RelationContext`
or wrappers around :func:`charmhelpers.core.hookenv.config`), and the actions
are just callbacks that are passed the service name for which they are executing
(or a subclass of :class:`~charmhelpers.core.services.base.ManagerCallback`
for more complex cases).

An example service definition might be::

  service_definitions = [
      {
          'service': 'wordpress',
          'ports': [80],
          'required_data': [config(), MySQLRelation()],
          'data_ready': [
              actions.install_frontend,
              services.render_template(source='wp-config.php.j2',
                                       target=os.path.join(WP_INSTALL_DIR, 'wp-config.php'))
              services.render_template(source='wordpress.upstart.j2',
                                       target='/etc/init/wordpress'),
          ],
      },
  ]

Each time a hook is fired, the conditions will be checked (in this case, just
that MySQL is available) and, if met, the appropriate actions taken (correct
front-end installed, config files written / updated, and the Upstart job
(re)started, implicitly).


Required Data Contexts
----------------------

Required data contexts are, at the most basic level, are just dictionaries,
and if they evaluate as True (e.g., if the contain data), their condition is
considered to be met.  A simple sentinal could just be a function that returns
data if available or an empty ``dict`` otherwise.

For the common case of gathering data from relations, the
:class:`~charmhelpers.core.services.helpers.RelationContext` base class gathers
data from a named relation and checks for a set of required keys to be present
and set on the relation before considering that relation complete.  For example,
a basic MySQL context might be::

  class MySQLRelation(RelationContext):
      name = 'db'
      interface = 'mysql'
      required_keys = ['host', 'user', 'password', 'database']

Because there could potentially be multiple units on a given relation, and
to prevent conflicts when the data contexts are merged to be sent to templates
(see below), the data for a ``RelationContext`` is nested in the following way::

  relation[relation.name][unit_number][relation_key]

For example, to get the host of the first MySQL unit (``mysql/0``)::

  mysql = MySQLRelation()
  unit_0_host = mysql[mysql.name][0]['host']

Note that only units that have set values for all of the required keys are
included in the list, and if no units have set all of the required keys,
instantiating the ``RelationContext`` will result in an empty list.


Data-Ready Actions
------------------

When a hook is triggered and all of the ``required_data`` contexts are complete,
the list of "data ready" actions are executed.  These callbacks are passed
the service name from the ``service`` key of the service definition for which
they are running, and are responsible for (re)configuring the service
according to the required data.

The most common action should be to render a config file from a template.
The :class:`render_template <charmhelpers.core.services.helpers.TemplateCallback>`
helper will merge all of the ``required_data`` contexts and render a
`Jinja2 <http://jinja.pocoo.org/>`_ template with the combined data.  For
example, to render a list of DSNs for units on the db relation, the
template should include::

  databases: [
    {% for unit in db %}
      "mysql://{{unit['user']}}:{{unit['password']}}@{{unit['host']}}/{{unit['database']}}",
    {% endfor %}
  ]

Note that the actions need to be idempotent, since they will all be re-run
if something about the charm changes (that is, if a hook is triggered).  That
is why rendering a template is preferred to editing a file via regular expression
substitutions.

Also note that the actions are not responsible for starting the service; there
are separate ``start`` and ``stop`` options that default to starting and stopping
an Upstart service with the name given by the ``service`` value.


Conclusion
----------

By using this framework, it is easy to see what the preconditions for the charm
are, and there is never a concern about things being in a partially configured
state.  As a charm author, you can focus on what is important to you: what
data is mandatory, what is optional, and what actions should be taken once
the requirements are met.
