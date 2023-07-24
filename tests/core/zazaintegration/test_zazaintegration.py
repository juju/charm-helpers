import os
import shutil
import subprocess
import sqlite3
import sys
import tempfile
import time
import unittest

import charmhelpers.core.unitdata as unitdata_mod
from charmhelpers.core.unitdata import Storage, kv

class ConcurrencyBase(unittest.TestCase):
    """Common logic for the failing and succeeding tests."""

    def setUp(self):
        # Start a separate process to lock the db (separate process to avoid
        # any sqlite sharing of connections)
        self.locking_proc = subprocess.Popen(
            [sys.executable, os.path.join(os.path.dirname(__file__), "subprocess_task.py")],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

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
            self.locking_proc.communicate(b"done\n", timeout=3)
        except subprocess.TimeoutExpired:
            self.locking_proc.kill()
            self.locking_proc.communicate()
        self.assertEqual(self.locking_proc.returncode, 0)


class ConcurrencySuccessTest(ConcurrencyBase):
    def setUp(self):
        # Add a fake zaza to the imports to see if that makes the store choose
        # :memory: by default.
        self.assertNotIn("zaza", sys.modules)
        sys.path.append(os.path.dirname(__file__))
        import zaza
        sys.path.remove(os.path.dirname(__file__))

        super().setUp()

    def test_concurrency(self):
        """Tests shouldn't write to same place."""

        self._concurrency_run()
        self.assertEqual(kv().db_path, ":memory:")

class ConcurrencyFailureTest(ConcurrencyBase):

    def setUp(self):
        # We create a special location to put the KV store so we can hammer it
        # without failing any other tox tests
        self.kv_dir = tempfile.mkdtemp()
        self.kv_file = os.path.join(self.kv_dir, "kvstore")
        os.environ["UNIT_STATE_DB"] = self.kv_file

        super().setUp()

    def tearDown(self):
        del os.environ["UNIT_STATE_DB"]
        shutil.rmtree(self.kv_dir)

    def test_concurrency_bug(self):
        """Check failure when writing to store while another process holds lock."""

        with self.assertRaisesRegex(sqlite3.OperationalError, "database is locked"):
            self._concurrency_run()


if __name__ == '__main__':
    unittest.main()
