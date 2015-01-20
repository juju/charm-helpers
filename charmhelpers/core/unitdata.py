#!/usr/bin/env python
# -*- coding: utf-8 -*-

#
# Copyright 2015 Canonical Ltd.
#
# Authors:
#  Kapil Thangavelu <kapil.foss@gmail.com>
#
"""
A simple way to carry state in units, supports versioned
and transactional operation.

from unitdata import kv
with kv.hook_scope():
   # do work
   kv.set('x', 1)

will automatically operate in a transaction.
"""

__author__ = 'Kapil Thangavelu <kapil.foss@gmail.com>'

import atexit
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
        self._init()

    def _scoped_query(self, stmt, params=None):
        if params is None:
            params = []
        return stmt, params
        if self.revision:
            stmt += " and revision=?"
            params.append(self.revision)
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
        stmt = "select key, data from kv where key like '%s_%%'" % key_prefix
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
        Store mapping and return a delta containing values that
        have changed.

        """
        previous = self.getrange(prefix, strip=True)
        pk = set(previous.keys())
        ck = set(mapping.keys())
        delta = DeltaSet()

        # added
        for k in ck.difference(pk):
            delta[k] = Delta((None, mapping[k]))

        # removed
        for k in pk.difference(ck):
            delta[k] = Delta((previous[k], None))

        # changed
        for k in pk.intersection(ck):
            c = mapping[k]
            p = previous[k]
            if c != p:
                delta[k] = Delta((p, c))

        if delta:
            return delta
        return None

    @contextlib.contextmanager
    def hook_scope(self, name, context=True):
        """Scope all future interactions to the current hook execution
        revision."""
        assert not self.revision
        self.cursor.execute(
            'insert into hooks (hook, date) values (?, ?)',
            (sys.argv[0],
             datetime.datetime.now().isoformat()))
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
        else:
            self.conn.rollback()

    def _init(self):
        self.cursor.execute('''
            create table kv (
               key text,
               data text,
               primary key (key)
               )''')
        self.cursor.execute('''
            create table kv_revisions (
               key text,
               revision integer,
               data text,
               primary key (key, revision)
               )''')
        self.cursor.execute('''
            create table hooks (
               version integer primary key autoincrement,
               hook text,
               date text
               )''')
        self.conn.commit()
        atexit.register(self.conn.commit)

    def gethistory(self, key):
        self.cursor.execute(
            'select revision, key, data from kv_revisions where key=?', [key])
        return self.cursor.fetchall()

    def debug(self):
        self.cursor.execute('select * from kv')
        pprint.pprint(self.cursor.fetchall())

        self.cursor.execute('select * from kv_revisions')
        import pprint
        pprint.pprint(self.cursor.fetchall())


class Record(dict):

    __slots__ = ()

    def __getattr__(self, k):
        if k in self:
            return self[k]
        raise AttributeError(k)


class DeltaSet(dict):

    __slots__ = ()

    def __getattr__(self, k):
        if k in self:
            return self[k]
        raise AttributeError(k)


class Delta(tuple):

    __slots__ = ()

    @property
    def current(self):
        return self[1]

    @property
    def previous(self):
        return self[0]


if 'CHARM_DIR' in os.environ:
    kv = Storage()
