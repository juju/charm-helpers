#!/usr/bin/env python
# -*- coding: utf-8 -*-

#
# Copyright 2015 Canonical Ltd.
#
# Authors:
#  Kapil Thangavelu <kapil.foss@gmail.com>
#
"""
Intro
-----

A simple way to carry state in units, supports versioned
and transactional operation.


Usage
-----
The preferred usage mode is via context manager::

  >>> from unitdata import kv
  >>> db = kv()
  >>> with db.hook_scope('install'):
  ...    # do work
  ...    db.set('x', 1)
  >>> db.get('x')
  1

will automatically use a transaction for operations within the with
block scope. It will also record the current hook name and timestamp
to provide additional context when looking at historical values.

Values are automatically json de/serialized to preserve basic typing
capabilities (ints, booleans, etc).

Individual values can be manipulated via get/set::

   >>> kv.set('y', True)
   >>> kv.get('y')
   True

Groups of keys can be manipulated with update/getrange::

   >>> kv.update({'z': 1, 'y': 2}, prefix="gui.")
   >>> kv.getrange('gui.', strip=True)
   {'z': 1, 'y': 2}

When updating values, its very helpful to understand which values
have actually changed and how have they changed. The storage
provides a delta method to provide for this::

   >>> data = {'debug': True, 'option': 2}
   >>> delta = kv.delta(data, 'config.')
   >>> delta.debug.previous
   None
   >>> delta.debug.current
   True
   >>> delta
   {'debug': (None, True), 'option': (None, 2)}

Note the delta method does not persist the actual change, it needs to
be explicitly saved via 'update' method::

   >>> kv.update(data, 'config.')

Values modified in the context of a hook scope retain historical values
associated to the hookname. History does not automatically json decode
values.

   >>> with db.hook_scope('config-changed'):
   ...      db.set('x', 42)
   >>> db.gethistory('x')
   [(1, u'x', u'1', u'install', u'2015-01-21T16:49:30.038372'),
    (2, u'x', u'42', u'config-changed', u'2015-01-21T16:49:30.038786')]

"""

__author__ = 'Kapil Thangavelu <kapil.foss@gmail.com>'

import collections
import contextlib
import datetime
import json
import os
import pprint
import sqlite3
import sys


class Storage(object):
    """Simple key value database for local unit state within charms.

    Modifications are automatically committed at hook exit. That's
    currently regardless of exit code.

    To support dicts, lists, integer, floats, and booleans values
    are automatically json encoded/decoded.
    """
    def __init__(self, path=None):
        self.db_path = path
        if path is None:
            self.db_path = os.path.join(
                os.environ.get('CHARM_DIR', ''), '.unit-state.db')
        self.conn = sqlite3.connect('%s' % self.db_path)
        self.cursor = self.conn.cursor()
        self.revision = None
        self._closed = False
        self._init()

    def close(self):
        if self._closed:
            return
        self.flush(False)
        self.cursor.close()
        self.conn.close()

    def _scoped_query(self, stmt, params=None):
        if params is None:
            params = []
        return stmt, params

    def get(self, key, default=None, record=False):
        self.cursor.execute(
            *self._scoped_query(
                'select data from kv where key=?', [key]))
        result = self.cursor.fetchone()
        if not result:
            return default
        if record:
            return Record(json.loads(result[0]))
        return json.loads(result[0])

    def getrange(self, key_prefix, strip=False):
        stmt = "select key, data from kv where key like '%s%%'" % key_prefix
        self.cursor.execute(*self._scoped_query(stmt))
        result = self.cursor.fetchall()

        if not result:
            return None
        if not strip:
            key_prefix = ''
        return dict([
            (k[len(key_prefix):], json.loads(v)) for k, v in result])

    def update(self, mapping, prefix=""):
        for k, v in mapping.items():
            self.set("%s%s" % (prefix, k), v)

    def unset(self, key):
        self.cursor.execute('delete from kv where key=?', [key])
        if self.revision:
            self.cursor.execute(
                'insert into kv_revisions values (?, ?, ?)',
                [self.revision, key, 'DELETED'])

    def set(self, key, value):
        serialized = json.dumps(value)

        self.cursor.execute(
            'select data from kv where key=?', [key])
        exists = self.cursor.fetchone()

        # Skip mutations to the same value
        if exists:
            if exists[0] == serialized:
                return value

        if not exists:
            self.cursor.execute(
                'insert into kv (key, data) values (?, ?)',
                (key, serialized))
        else:
            self.cursor.execute('''
            update kv
            set data = ?
            where key = ?''', [serialized, key])

        # Save
        if not self.revision:
            return value

        self.cursor.execute(
            'select 1 from kv_revisions where key=? and revision=?',
            [key, self.revision])
        exists = self.cursor.fetchone()

        if not exists:
            self.cursor.execute(
                '''insert into kv_revisions (
                revision, key, data) values (?, ?, ?)''',
                (self.revision, key, serialized))
        else:
            self.cursor.execute(
                '''
                update kv_revisions
                set data = ?
                where key = ?
                and   revision = ?''',
                [serialized, key, self.revision])

        return value

    def delta(self, mapping, prefix):
        """
        return a delta containing values that have changed.
        """
        previous = self.getrange(prefix, strip=True)
        if not previous:
            pk = set()
        else:
            pk = set(previous.keys())
        ck = set(mapping.keys())
        delta = DeltaSet()

        # added
        for k in ck.difference(pk):
            delta[k] = Delta(None, mapping[k])

        # removed
        for k in pk.difference(ck):
            delta[k] = Delta(previous[k], None)

        # changed
        for k in pk.intersection(ck):
            c = mapping[k]
            p = previous[k]
            if c != p:
                delta[k] = Delta(p, c)

        if delta:
            return delta
        return None

    @contextlib.contextmanager
    def hook_scope(self, name="", context=True):
        """Scope all future interactions to the current hook execution
        revision."""
        assert not self.revision
        self.cursor.execute(
            'insert into hooks (hook, date) values (?, ?)',
            (name or sys.argv[0],
             datetime.datetime.utcnow().isoformat()))
        self.revision = self.cursor.lastrowid
        if not context:
            yield self.revision
            raise StopIteration()
        try:
            yield self.revision
            self.revision = None
        except:
            self.flush(False)
            self.revision = None
            raise
        else:
            self.flush()

    def flush(self, save=True):
        if save:
            self.conn.commit()
        elif self._closed:
            return
        else:
            self.conn.rollback()

    def _init(self):
        self.cursor.execute('''
            create table if not exists kv (
               key text,
               data text,
               primary key (key)
               )''')
        self.cursor.execute('''
            create table if not exists kv_revisions (
               key text,
               revision integer,
               data text,
               primary key (key, revision)
               )''')
        self.cursor.execute('''
            create table if not exists hooks (
               version integer primary key autoincrement,
               hook text,
               date text
               )''')
        self.conn.commit()

    def gethistory(self, key):
        self.cursor.execute(
            '''
            select kv.revision, kv.key, kv.data, h.hook, h.date
            from kv_revisions kv,
                 hooks h
            where kv.key=?
             and kv.revision = h.version
            ''', [key])
        return self.cursor.fetchall()

    def debug(self):
        self.cursor.execute('select * from kv')
        pprint.pprint(self.cursor.fetchall())
        self.cursor.execute('select * from kv_revisions')
        pprint.pprint(self.cursor.fetchall())


class Record(dict):

    __slots__ = ()

    def __getattr__(self, k):
        if k in self:
            return self[k]
        raise AttributeError(k)


class DeltaSet(Record):

    __slots__ = ()


Delta = collections.namedtuple('Delta', ['previous', 'current'])


_KV = None


def kv():
    global _KV
    if _KV is None:
        _KV = Storage()
    return _KV
