import os
import threading
from hashlib import sha1
try:
    import cPickle as pickle
except ImportError:
    import pickle

from zope.interface import implements
from zope.interface import directlyProvides

from repoze.accelerator.interfaces import IChunkHandler
from repoze.accelerator.interfaces import IStorage
from repoze.accelerator.interfaces import IStorageFactory
from repoze.accelerator.locks import Locks

class MemoryStorage:
    implements(IStorage)

    def __init__(self, logger, lock=threading.Lock()):
        self.logger = logger
        self.data = {}
        self.lock = lock

    def store(self, url, discriminators, expires, status, headers, **extras):
        body = []
        storage = self

        class SimpleHandler:
            implements(IChunkHandler)
            def write(self, chunk):
                body.append(chunk)

            def close(self):
                storage.lock.acquire()
                try:
                    entries = storage.data.setdefault(url, {})
                    entries[discriminators] = expires,status,headers,body,extras
                finally:
                    storage.lock.release()

        return SimpleHandler()
                
    def fetch(self, url):
        entries = self.data.get(url)
        if entries is None:
            return
        for discrims, (expires,status,headers,body,extras) in entries.items():
            yield (discrims, expires, status, headers, body, extras)

def make_memory_storage(logger, config):
    return MemoryStorage(logger)
directlyProvides(make_memory_storage, IStorageFactory)

class DiskStorage(object):
    implements(IStorage)
    def __init__(self, logger, path):
        self.logger = logger
        self.path = path
        self.locks = Locks()
    
    @staticmethod
    def _safe_hash(string):
        sha1sum = sha1()
        sha1sum.update(string)
        return sha1sum.hexdigest()

    def _dirname(self, url):
        hashedname = self._safe_hash(url)
        return os.path.join(self.path, hashedname[0:2], hashedname[2:])

    def contents(self, url):
        subdir = self._dirname(url)
        if os.path.exists(subdir):
            for each in os.listdir(subdir):
                if each.lower().endswith(".body"):
                    continue
                yield os.path.join(subdir, each)

    def store(self, url, discriminators, expires, status, headers, **extras):
        subdir = self._dirname(url)
        os.makedirs(subdir)
        key = self._safe_hash(pickle.dumps(discriminators))
        filename = os.path.join(subdir, key)
        fp = open(filename, 'w')
        lock = self.locks.acquire(filename, fp)

        pickle.dump((discriminators, expires, status, headers, extras), fp)
        body_filename = filename + ".body"
        if os.path.exists(body_filename):
            os.unlink(body_filename)
        body = open(body_filename, "w")    
        
        fp.close()
        lock.release()

        class SimpleHandler:
            implements(IChunkHandler)
            def write(self, chunk):
                body.write(chunk)

            def close(self):
                body.close()

        return SimpleHandler()

    def fetch(self, url):
        for each in self.contents(url):
            fp = open(each, "r")
            lock = self.locks.acquire(each, fp)
            try:
                values = pickle.load(fp)
                (discrims, expires, status, headers, extras) = values
                body = open(each + ".body", "r")
                yield (discrims, expires, status, headers, body, extras)
            finally:
                lock.release()
                fp.close

def make_disk_storage(logger, config):
    path = config['storage.path']
    return DiskStorage(logger, path)
directlyProvides(make_disk_storage, IStorageFactory)

