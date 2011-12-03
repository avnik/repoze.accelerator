"""Very naive locking
TODO: add tests
TODO: add flock
"""
import threading

class Lock(object):
    def __init__(self, parent, name, fp):
        self.parent = parent
        self.name = name
        self.fp = fp
        self.lock = threading.Lock()

    def release(self):
        self.lock.release()
        self.parent.mutex.acquire()
        try:
            del self.parent.locks[self.name]
        finally:
            self.parent.mutex.release()

class Locks(object):
    def __init__(self):
        self.locks = {}
        self.mutex = threading.Lock()

    def acquire(self, filename, fp):
        self.mutex.acquire()
        try:
            self.locks.setdefault(filename, threading.Lock())
            lock = self.locks[filename]
        finally:
            self.mutex.release()
        lock.acquire()
        return lock
