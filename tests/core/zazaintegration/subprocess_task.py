from charmhelpers.core.unitdata import kv

def locking_thread():
    store = kv()
    # Force a long interaction with the sqlite db
    store.cursor.execute("BEGIN EXCLUSIVE TRANSACTION")
    # Await input to know when the test is over
    x = input()
    store.conn.commit()

if __name__ == '__main__':
    locking_thread()
