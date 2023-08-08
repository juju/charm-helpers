import os
import subprocess
import sqlite3
import sys
import time
import unittest

import charmhelpers.core.unitdata as unitdata_mod
from charmhelpers.core.unitdata import kv


class ConcurrencyBase(unittest.TestCase):
    """Common logic for the failing and succeeding tests."""

    def setUp(self):
        # Start a separate process to lock the db (separate process to avoid
        # any sqlite sharing of connections)

        # Need to copy the current path into the subprocess too
        subproc_env = os.environ.copy()
        subproc_env["PYTHONPATH"] = ":".join(sys.path)
        self.locking_proc = subprocess.Popen(
            [sys.executable, os.path.join(os.path.dirname(__file__), "subprocess_task.py")],
            env=subproc_env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        # Undo any prior test's setup of _KV
        unitdata_mod._KV = None

        @self.addCleanup
        def cleanup_kv():
            unitdata_mod._KV = None
            if self.locking_proc.returncode is None:
                self.locking_proc.kill()
                self.locking_proc.communicate()

    def _concurrency_run(self):
        store = kv()
        for i in range(3):
            store.set(str(i), i)
            # This commit line seems necessary to allow the subprocess to lock
            # the db.
            store.conn.commit()
            time.sleep(1)

        try:
            outs, errs = self.locking_proc.communicate(b"done\n", timeout=3)
            if self.locking_proc.returncode != 0:
                print("Subprocess failed\nstdout={outs}\nstderr={errs}"
                      .format(outs=outs, errs=errs))
        except subprocess.TimeoutExpired:
            self.locking_proc.kill()
            outs, errs = self.locking_proc.communicate()
            print("Had to kill subprocess\nstdout={outs}\nstderr={errs}"
                  .format(outs=outs, errs=errs))
        self.assertEqual(self.locking_proc.returncode, 0)


class ConcurrencySuccessTest(ConcurrencyBase):
    def setUp(self):
        # We must have no JUJU_* environment variables that have been leftover
        # from previous tests while running this test.
        for key in list(os.environ):
            if key.startswith("JUJU_"):
                del os.environ[key]

        super().setUp()

    def test_concurrency(self):
        """Tests shouldn't write to same place."""

        # This test suite used to require setting env vars but now the default
        # behaviour should be to detect we are not running inside of a juju
        # agent.
        self._concurrency_run()
        self.assertEqual(kv().db_path, ":memory:")


class ConcurrencyFailureTest(ConcurrencyBase):

    def setUp(self):
        os.environ["JUJU_UNIT_NAME"] = "fakeunit/0"

        super().setUp()

    def tearDown(self):
        if "JUJU_UNIT_NAME" in os.environ:
            del os.environ["JUJU_UNIT_NAME"]

    def test_concurrency_bug(self):
        """Check failure when writing to store while another process holds lock."""

        with self.assertRaisesRegex(sqlite3.OperationalError, "database is locked"):
            self._concurrency_run()


class ConcurrencyForceTestModeTest(ConcurrencyBase):

    def setUp(self):
        os.environ["JUJU_UNIT_NAME"] = "fakeunit/0"
        os.environ["CHARM_HELPERS_TESTMODE"] = "yes"

        super().setUp()

    def tearDown(self):
        if "JUJU_UNIT_NAME" in os.environ:
            del os.environ["JUJU_UNIT_NAME"]
        if "CHARM_HELPERS_TESTMODE" in os.environ:
            del os.environ["CHARM_HELPERS_TESTMODE"]

    def test_in_memory(self):
        """Check success when forcing test mode despite faking juju execution."""

        self._concurrency_run()
        self.assertEqual(kv().db_path, ":memory:")


if __name__ == '__main__':
    unittest.main()
