"""Tests for lakshmi.cache module."""
import pickle
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import lakshmi.cache as cache


class Cached(cache.Cacheable):
    def __init__(self, key, value):
        self.key = key
        self.value = value

    def cache_key(self):
        return self.key

    @cache.cache(2)
    def get_value(self):
        return self.value

    @cache.cache(365)
    def get_long_cached_value(self):
        return self.value


class CacheTest(unittest.TestCase):
    def setUp(self):
        # Reset cache dir setting.
        cache._prefetch_obj = None
        cache._ctx.pop(cache._CACHE_STR, None)
        cache.set_force_refresh(False)
        cache.set_cache_miss_func(None)

    @patch('pathlib.Path.exists')
    @patch('lakshmi.cache.get_file_age')
    def test_disabled_cache(self, get_file_age, exists):
        cache.set_cache_dir(None)  # Disble caching.
        c = Cached('key1', 1)
        self.assertEqual(1, c.get_value())
        c.value = 2
        self.assertEqual(2, c.get_value())
        get_file_age.assert_not_called()
        exists.assert_not_called()

    def test_disabled_cache_with_func(self):
        cache.set_cache_dir(None)  # Disble caching.
        mocked_obj = Mock()
        cache.set_cache_miss_func(mocked_obj.func)

        c = Cached('key1', 1)
        self.assertEqual(1, c.get_value())
        mocked_obj.func.assert_called_once()

    @patch('pathlib.Path.read_bytes')
    @patch('pathlib.Path.write_bytes')
    @patch('pathlib.Path.exists')
    @patch('lakshmi.cache.get_file_age')
    @patch('lakshmi.cache.set_cache_dir')
    def test_default_cache_miss(
            self, set_cache_dir, get_file_age, exists, write_bytes,
            read_bytes):
        def side_effect(x):
            cache._ctx[cache._CACHE_STR] = x
        set_cache_dir.side_effect = side_effect
        exists.return_value = False

        c = Cached('key1', 1)
        self.assertEqual(1, c.get_value())

        set_cache_dir.assert_called_once()
        get_file_age.assert_not_called()
        exists.assert_called_once()
        write_bytes.assert_called_once_with(pickle.dumps(1))
        read_bytes.assert_not_called()

    @patch('pathlib.Path.write_bytes')
    @patch('pathlib.Path.exists')
    @patch('lakshmi.cache.set_cache_dir')
    def test_default_cache_miss_with_func(
            self, set_cache_dir, exists, write_bytes):
        def side_effect(x):
            cache._ctx[cache._CACHE_STR] = x
        set_cache_dir.side_effect = side_effect
        exists.return_value = False
        mocked_obj = Mock()
        cache.set_cache_miss_func(mocked_obj.func)

        c = Cached('key1', 1)
        self.assertEqual(1, c.get_value())

        set_cache_dir.assert_called_once()
        exists.assert_called_once()
        write_bytes.assert_called_once_with(pickle.dumps(1))
        mocked_obj.func.assert_called_once()

    @patch('pathlib.Path.read_bytes')
    @patch('pathlib.Path.write_bytes')
    @patch('pathlib.Path.exists')
    @patch('lakshmi.cache.get_file_age')
    @patch('lakshmi.cache.set_cache_dir')
    def test_default_cache_hit(
            self, set_cache_dir, get_file_age, exists, write_bytes,
            read_bytes):
        def side_effect(x):
            cache._ctx[cache._CACHE_STR] = x
        set_cache_dir.side_effect = side_effect
        exists.return_value = True
        get_file_age.return_value = 1
        read_bytes.return_value = pickle.dumps(1)  # Cache 1.

        c = Cached('key2', 2)
        self.assertEqual(1, c.get_value())  # Cached value.

        set_cache_dir.assert_called_once()
        get_file_age.assert_called_once()
        exists.assert_called_once()
        write_bytes.assert_not_called()
        read_bytes.assert_called_once()

    @patch('pathlib.Path.read_bytes')
    @patch('pathlib.Path.exists')
    @patch('lakshmi.cache.get_file_age')
    @patch('lakshmi.cache.set_cache_dir')
    def test_default_cache_hit_with_func(
            self, set_cache_dir, get_file_age, exists, read_bytes):
        def side_effect(x):
            cache._ctx[cache._CACHE_STR] = x
        set_cache_dir.side_effect = side_effect
        exists.return_value = True
        get_file_age.return_value = 1
        read_bytes.return_value = pickle.dumps(1)  # Cache 1.
        mocked_obj = Mock()
        cache.set_cache_miss_func(mocked_obj.func)

        c = Cached('key2', 2)
        self.assertEqual(1, c.get_value())  # Cached value.

        set_cache_dir.assert_called_once()
        get_file_age.assert_called_once()
        exists.assert_called_once()
        read_bytes.assert_called_once()
        mocked_obj.func.assert_not_called()

    @patch('pathlib.Path.read_bytes')
    @patch('pathlib.Path.write_bytes')
    @patch('pathlib.Path.exists')
    @patch('lakshmi.cache.get_file_age')
    @patch('lakshmi.cache.set_cache_dir')
    def test_set_cache(
            self, set_cache_dir, get_file_age, exists, write_bytes,
            read_bytes):
        cache._ctx[cache._CACHE_STR] = Path('/fake/dir')
        exists.return_value = False

        c = Cached('key1', 1)
        self.assertEqual(1, c.get_value())

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
    def test_force_refresh(
            self, set_cache_dir, get_file_age, exists, write_bytes,
            read_bytes):
        cache._ctx[cache._CACHE_STR] = Path('/fake/dir')
        cache.set_force_refresh(True)

        c = Cached('key2', 2)
        self.assertEqual(2, c.get_value())  # Cached value not used.

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
    def test_force_refresh_with_long_cached_value(
            self, set_cache_dir, get_file_age, exists, write_bytes,
            read_bytes):
        cache._ctx[cache._CACHE_STR] = Path('/fake/dir')
        cache.set_force_refresh(True)
        exists.return_value = True
        get_file_age.return_value = 5
        read_bytes.return_value = pickle.dumps(1)  # Cache 1.

        c = Cached('key2', 2)
        self.assertEqual(1, c.get_long_cached_value())  # Cached value.

        set_cache_dir.assert_not_called()
        get_file_age.assert_called_once()
        exists.assert_called_once()
        write_bytes.assert_not_called()
        read_bytes.assert_called_once()

    @patch('pathlib.Path.read_bytes')
    @patch('pathlib.Path.write_bytes')
    @patch('pathlib.Path.exists')
    @patch('lakshmi.cache.get_file_age')
    @patch('lakshmi.cache.set_cache_dir')
    def test_force_refresh_called_twice(
            self, set_cache_dir, get_file_age, exists, write_bytes,
            read_bytes):
        # While this test is not logically "correct", it makes the
        # testing easier and more robust. In reality the cached
        # value would be 2 and not 3.
        cache._ctx[cache._CACHE_STR] = Path('/fake/dir')
        cache.set_force_refresh(True)
        get_file_age.return_value = 1
        read_bytes.return_value = pickle.dumps(3)  # Cache 3.

        c = Cached('key2', 2)
        self.assertEqual(2, c.get_value())  # Cached value not used.
        self.assertEqual(3, c.get_value())  # Cached value used.

        set_cache_dir.assert_not_called()
        get_file_age.assert_called_once()
        exists.assert_called_once()
        write_bytes.assert_called_once_with(pickle.dumps(2))
        read_bytes.assert_called_once()

    @patch('pathlib.Path.read_bytes')
    @patch('pathlib.Path.write_bytes')
    @patch('pathlib.Path.exists')
    @patch('lakshmi.cache.get_file_age')
    @patch('lakshmi.cache.set_cache_dir')
    def test_old_cache(
            self, set_cache_dir, get_file_age, exists, write_bytes,
            read_bytes):
        cache._ctx[cache._CACHE_STR] = Path('/fake/dir')
        exists.return_value = True
        get_file_age.return_value = 2

        c = Cached('key1', 1)
        self.assertEqual(1, c.get_value())

        set_cache_dir.assert_not_called()
        get_file_age.assert_called_once()
        exists.assert_called_once()
        write_bytes.assert_called_once_with(pickle.dumps(1))
        read_bytes.assert_not_called()

    @patch('lakshmi.cache.set_cache_dir')
    def test_return_cached_funcs(self, set_cache_dir):
        def side_effect(x):
            cache._ctx[cache._CACHE_STR] = x
        set_cache_dir.side_effect = side_effect
        prefetch = cache._Prefetch()
        c = Cached('key1', 1)
        self.assertEqual(2, len(prefetch._return_cached_funcs(c)))

    @patch('pathlib.Path.read_bytes')
    @patch('pathlib.Path.write_bytes')
    @patch('pathlib.Path.exists')
    @patch('lakshmi.cache.get_file_age')
    @patch('lakshmi.cache.set_cache_dir')
    def test_cache_miss_prefetch(
            self, set_cache_dir, get_file_age, exists, write_bytes,
            read_bytes):
        def side_effect(x):
            cache._ctx[cache._CACHE_STR] = x
        set_cache_dir.side_effect = side_effect
        exists.return_value = False

        c = Cached('key1', 1)
        cache.prefetch_add(c)
        cache.prefetch()

        set_cache_dir.assert_called_once()
        get_file_age.assert_not_called()
        exists.assert_called()
        self.assertEqual(2, write_bytes.call_count)
        read_bytes.assert_not_called()

    @patch('pathlib.Path.read_bytes')
    @patch('pathlib.Path.write_bytes')
    @patch('pathlib.Path.exists')
    @patch('lakshmi.cache.get_file_age')
    @patch('lakshmi.cache.set_cache_dir')
    def test_force_refresh_with_prefetch(
            self, set_cache_dir, get_file_age, exists, write_bytes,
            read_bytes):
        cache._ctx[cache._CACHE_STR] = Path('/fake/dir')
        cache.set_force_refresh(True)
        get_file_age.return_value = 2

        c = Cached('key2', 9)
        cache.prefetch_add(c)
        cache.prefetch()
        self.assertEqual(9, c.get_value())

        set_cache_dir.assert_not_called()
        self.assertEqual(2, get_file_age.call_count)
        self.assertEqual(2, exists.call_count)
        self.assertEqual(2, write_bytes.call_count)
        read_bytes.assert_not_called()

    def test_prefetch_add_not_called(self):
        # Do not fail if there are no functions to be prefetched.
        cache.prefetch()


if __name__ == '__main__':
    unittest.main()
