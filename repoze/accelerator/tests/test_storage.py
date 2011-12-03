import unittest

_MARKER = object()

class BaseStorageTest(object):
    def test_class_conforms_to_IStorage(self):
        from zope.interface.verify import verifyClass
        from repoze.accelerator.interfaces import IStorage
        verifyClass(IStorage, self._getTargetClass())

    def test_instance_conforms_to_IStorage(self):
        from zope.interface.verify import verifyObject
        from repoze.accelerator.interfaces import IStorage
        verifyObject(IStorage, self._makeOne(DummyLock()))

    def test_factory_provides_IStorageFactory(self):
        from zope.interface.verify import verifyObject
        from repoze.accelerator.interfaces import IStorageFactory
        from repoze.accelerator.storage import make_memory_storage
        verifyObject(IStorageFactory, make_memory_storage)

class TestMemoryStorage(unittest.TestCase, BaseStorageTest):
    def _getTargetClass(self):
        from repoze.accelerator.storage import MemoryStorage
        return MemoryStorage

    def _makeOne(self, lock):
        klass = self._getTargetClass()
        logger = None
        return klass(logger, lock)

    def test_store_nonexistent(self):
        lock = DummyLock()
        storage = self._makeOne(lock)
        headers = [('Header1', 'value1')]
        handler = storage.store('url', (), 0, 'status', headers)
        self.failIf(handler is None)
        chunks = ['chunk1', 'chunk2']
        for chunk in ('chunk1', 'chunk2'):
            handler.write(chunk)
        handler.close()
        self.assertEqual(storage.data['url'][()],
                         (0, 'status', headers, chunks, {}))
        self.assertEqual(lock.acquired, 1)
        self.assertEqual(lock.released, 1)

    def test_store_existing(self):
        lock = DummyLock()
        storage = self._makeOne(lock)
        storage.data['url'] = {}
        storage.data['url'][(), ()] = ('otherstatus', (), ())
        headers = [('Header1', 'value1')]
        handler = storage.store('url', (), 0, 'status', headers)
        self.failIf(handler is None)
        chunks = ['chunk1', 'chunk2']
        for chunk in ('chunk1', 'chunk2'):
            handler.write(chunk)
        handler.close()
        self.assertEqual(storage.data['url'][()],
                         (0, 'status', headers, chunks, {}))
        self.assertEqual(lock.acquired, 1)
        self.assertEqual(lock.released, 1)

    def test_fetch_nonexistent(self):
        lock = DummyLock()
        storage = self._makeOne(lock)
        self.assertEqual(len(list(storage.fetch('url'))), 0)

    def test_fetch_existing(self):
        lock = DummyLock()
        storage = self._makeOne(lock)
        storage.data['url'] = {
            ('env', (1, 2)):(0, 200, [], [], {}),
            ('env', (3, 4)):(0, 203, [], [], {}),
            }
        result = list(iter(storage.fetch('url')))
        result.sort()
        self.assertEqual(len(result), 2)
        self.assertEqual(
            result[0],
            (('env', (1,2)), 0, 200, [], [], {})
            )
        self.assertEqual(
            result[1],
            (('env', (3,4)), 0, 203, [], [], {})
            )

    def test_storage_factory_defaults(self):
        from repoze.accelerator.storage import make_memory_storage
        storage = make_memory_storage(None, {})
        self.assertEqual(storage.logger, None)

#FIXME: add more tests
class TestDiskStorage(unittest.TestCase, BaseStorageTest):
    def _getTargetClass(self):
        from repoze.accelerator.storage import DiskStorage
        return DiskStorage

    def _makeOne(self, lock):
        klass = self._getTargetClass()
        logger = None
        path = self._tempdir
        return klass(logger, path)

    def setUp(self):
        import tempfile
        self._tempdir = tempfile.mkdtemp()

    def tearDown(self):
        import os
        import shutil
        if os.path.exists(self._tempdir):
            shutil.rmtree(self._tempdir)

    def test_storage_factory_defaults(self):
        from repoze.accelerator.storage import make_disk_storage
        storage = make_disk_storage(None, {"storage.path": self._tempdir})
        self.assertEqual(storage.logger, None)

    def test_store_nonexistent(self):
        lock = DummyLock()
        storage = self._makeOne(lock)
        headers = [('Header1', 'value1')]
        handler = storage.store('url', (), 0, 'status', headers)
        self.failIf(handler is None)
        chunks = ['chunk1', 'chunk2']
        for chunk in ('chunk1', 'chunk2'):
            handler.write(chunk)
        handler.close()

        data = list(iter(storage.fetch('url')))[0]
        disc, expires, status, headers_, body, extra = data
        body = "".join(list(iter(body)))
        self.assertEqual(status, "status")
        self.assertEqual(headers_, headers)
        self.assertEqual(body, "".join(chunks))

class DummyLock:
    def __init__(self):
        self.acquired = 0
        self.released = 0

    def acquire(self):
        self.acquired += 1

    def release(self):
        self.released += 1

