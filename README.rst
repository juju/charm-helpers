CharmHelpers |badge|
--------------------

.. |badge| image:: https://travis-ci.org/juju/charm-helpers.svg?branch=master
    :target: https://travis-ci.org/juju/charm-helpers

Overview
========

CharmHelpers provides an opinionated set of tools for building Juju charms.

The full documentation is available online at: https://charm-helpers.readthedocs.io/

Common Usage Examples
=====================

* interaction with charm-specific Juju unit agents via hook tools;
* processing of events and execution of decorated functions based on event names;
* handling of persistent storage between independent charm invocations;
* rendering of configuration file templates;
* modification of system configuration files;
* installation of packages;
* retrieval of machine-specific details;
* implementation of application-specific code reused in similar charms.

Why Python?
===========

* Python is an extremely popular, easy to learn, and powerful language which is also common in automation tools;
* An interpreted language helps with charm portability across different CPU architectures;
* Doesn't require debugging symbols (just use pdb in-place);
* An author or a user is able to make debugging changes without recompiling a charm.

License
=======

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

 http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
