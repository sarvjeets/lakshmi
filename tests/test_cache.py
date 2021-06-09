"""Tests for lakshmi.cache module."""
import lakshmi.cache as cache
from hashlib import md5
from unittest.mock import patch
from pathlib import Path
import pickle
import unittest


class Cached(cache.Cacheable):
    def __init__(self, key, value):
        self.key = key
        self.value = value

    def CacheKey(self):
        return self.key

    @cache.cache(2)
    def Value(self):
        return self.value


class CacheTest(unittest.TestCase):
    def setUp(self):
        # Reset cache dir setting.
        cache._ctx.pop(cache._CACHE_STR, None)
        cache.set_force_refresh(False)

    @patch('pathlib.Path.exists')
    @patch('lakshmi.cache.get_file_age')
    def testDisabledCache(self, get_file_age, exists):
        cache.set_cache_dir(None)  # Disble caching.
        c = Cached('key1', 1)
        self.assertEqual(1, c.Value())
        c.value = 2
        self.assertEqual(2, c.Value())
        get_file_age.assert_not_called()
        exists.assert_not_called()

    @patch('pathlib.Path.read_bytes')
    @patch('pathlib.Path.write_bytes')
    @patch('pathlib.Path.exists')
    @patch('lakshmi.cache.get_file_age')
    @patch('lakshmi.cache.set_cache_dir')
    def testDefaultCacheMiss(self, set_cache_dir, get_file_age, exists,
                             write_bytes, read_bytes):
        def side_effect(x):
            cache._ctx[cache._CACHE_STR] = x
        set_cache_dir.side_effect = side_effect
        exists.return_value = False

        c = Cached('key1', 1)
        self.assertEqual(1, c.Value())

        set_cache_dir.assert_called_once()
        get_file_age.assert_not_called()
        exists.assert_called_once()
        write_bytes.assert_called_once_with(pickle.dumps(1))
        read_bytes.assert_not_called()

    @patch('pathlib.Path.read_bytes')
    @patch('pathlib.Path.write_bytes')
    @patch('pathlib.Path.exists')
    @patch('lakshmi.cache.get_file_age')
    @patch('lakshmi.cache.set_cache_dir')
    def testDefaultCacheHit(self, set_cache_dir, get_file_age, exists,
                            write_bytes, read_bytes):
        def side_effect(x):
            cache._ctx[cache._CACHE_STR] = x
        set_cache_dir.side_effect = side_effect
        exists.return_value = True
        get_file_age.return_value = 1
        read_bytes.return_value = pickle.dumps(1)  # Cache 1.

        c = Cached('key2', 2)
        self.assertEqual(1, c.Value())  # Cached value.

        set_cache_dir.assert_called_once()
        get_file_age.assert_called_once()
        exists.assert_called_once()
        write_bytes.assert_not_called()
        read_bytes.assert_called_once()

    @patch('pathlib.Path.read_bytes')
    @patch('pathlib.Path.write_bytes')
    @patch('pathlib.Path.exists')
    @patch('lakshmi.cache.get_file_age')
    @patch('lakshmi.cache.set_cache_dir')
    def testSetCache(self, set_cache_dir, get_file_age, exists,
                     write_bytes, read_bytes):
        cache._ctx[cache._CACHE_STR] = Path('/fake/dir')
        exists.return_value = False

        c = Cached('key1', 1)
        self.assertEqual(1, c.Value())

        set_cache_dir.assert_not_called()
        get_file_age.assert_not_called()
        exists.assert_called_once()
        write_bytes.assert_called_once_with(pickle.dumps(1))
        read_bytes.assert_not_called()

    @patch('pathlib.Path.read_bytes')
    @patch('pathlib.Path.write_bytes')
    @patch('pathlib.Path.exists')
    @patch('lakshmi.cache.get_file_age')
    @patch('lakshmi.cache.set_cache_dir')
    def testForceRefresh(self, set_cache_dir, get_file_age, exists,
                         write_bytes, read_bytes):
        cache._ctx[cache._CACHE_STR] = Path('/fake/dir')
        cache.set_force_refresh(True)

        c = Cached('key2', 2)
        self.assertEqual(2, c.Value())  # Cached value not used.

        set_cache_dir.assert_not_called()
        get_file_age.assert_not_called()
        exists.assert_not_called()
        write_bytes.assert_called_once_with(pickle.dumps(2))
        read_bytes.assert_not_called()

    @patch('pathlib.Path.read_bytes')
    @patch('pathlib.Path.write_bytes')
    @patch('pathlib.Path.exists')
    @patch('lakshmi.cache.get_file_age')
    @patch('lakshmi.cache.set_cache_dir')
    def testOldCache(self, set_cache_dir, get_file_age, exists,
                     write_bytes, read_bytes):
        cache._ctx[cache._CACHE_STR] = Path('/fake/dir')
        exists.return_value = True
        get_file_age.return_value = 2

        c = Cached('key1', 1)
        self.assertEqual(1, c.Value())

        set_cache_dir.assert_not_called()
        get_file_age.assert_called_once()
        exists.assert_called_once()
        write_bytes.assert_called_once_with(pickle.dumps(1))
        read_bytes.assert_not_called()


if __name__ == '__main__':
    unittest.main()
