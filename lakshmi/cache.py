"""
This class is used to cache return value of functions on disk for a specified
number of days. This is used by lakshmi.assets module to cache name/ asset
value (i.e the slow functions). For examples on how to use this class, please
see the tests (tests/test_cache.py file).

Currently, this module can only be used on functions which are class members
and the function itself must take no arguments. These restrictions can be
easily relaxed, but so far that all usecases don't need anything more than what
is currently implemented.

In addition to caching values, this class also allows one to optionally call
a user-specified function on cache-misses (currently used to show a progress
bar to the user via the lak CLI).
"""

import concurrent.futures
import functools
import pickle
from abc import ABC, abstractmethod
from datetime import datetime
from hashlib import md5
from pathlib import Path

# Inspired by https://pypi.org/project/cache-to-disk/. I tried using other
# options such as requests-cache, but it was too slow compared to the solution
# implemented here.


class Cacheable(ABC):
    """Interface that declares that a particular class's method return
    values could be cached. The methods should not take a parameter,
    and cache_key() + method name should uniquely imply the return
    value of that class method."""
    @abstractmethod
    def cache_key(self):
        """Unique string value used as key for caching."""
        pass


def get_file_age(file):
    """Returns the age of file.

    Args:
        file: A PosixPath object representing a file.

    Returns: An int represeting the age in days.
    """
    return (datetime.today()
            - datetime.fromtimestamp(file.stat().st_mtime)).days


# Constants
# Default cache directory if none is specified.
_DEFAULT_DIR = Path.home() / '.lakshmicache'

_CACHE_STR = 'cache_dir'
_FORCE_STR = 'force_refresh'
_FORCED_FILES_STR = 'forced_files'
_MISS_FUNC_STR = 'miss_func'

# Dict (string -> object) to keep cache context.
# Description of keys to what is stored:
# _CACHE_STR:
# The pathlib.Path object specifying cache directory. If set to None,
# caching is disabled. Default: _DEFAULT_DIR
# _FORCE_STR:
# If set to True, new values are re-generated once even if a cached one is
# available. This is meant for data that is cached for < month (stock prices
# and Treasury Bond value). Values that are cached for > 40 days ignore this
# flag. Default: False
# _FORCED_FILES_STR:
# A set of files which are already refreshed once due to _ctx[_FORCE_STR]
# being set to True. this is used to ensure we don't re-fetch same values
# multiple times in a session.
# _MISS_FUNC_STR:
# If set, this function is called for every cache miss.
_ctx = {_FORCE_STR: False}


def set_force_refresh(v):
    """Sets whether cached values should be refreshed.

    Args:
        v: Boolean representing if cached values should be re-generated.
    """
    global _ctx
    _ctx[_FORCE_STR] = v
    _ctx[_FORCED_FILES_STR] = set()


def set_cache_miss_func(f):
    """Sets the function to call for cache-misses in case the cached function
    is directly called. This func is called periodically if prefetch() is
    used to fetch multiple cached values. This is useful for displaying
    progress bar while waiting for slow functions to complete.

    Args:
        f: The function to call whenever a cache-miss happens (i.e. whenever
        the underlying function is called instead of using a cached value) OR
        this function is called periodically when using prefetch to fetch
        multiple values in parallel.
    """
    global _ctx
    if f:
        _ctx[_MISS_FUNC_STR] = f
    else:
        # Clear out previously set function, if any.
        _ctx.pop(_MISS_FUNC_STR, None)


def set_cache_dir(cache_dir):
    """Sets the cache directory.

    If the cache directory is not specified, default ~/.lakshmicache
    is used.

    Args:
        cache_dir: The pathlib.Path object specifying cache directory.
        If set to None, caching is disabled.
    """
    global _ctx
    _ctx[_CACHE_STR] = cache_dir
    if cache_dir is None:
        return
    cache_dir.mkdir(exist_ok=True)  # Create cache dir if one doesn't exist.
    # Delete old files whose cache values are invalid already.
    for file in cache_dir.glob('*_*.lkc'):
        days = int(file.name.split('_')[0])
        if get_file_age(file) >= days:
            file.unlink()


def _valid_cached_value(file, days, add_to_ignored=True):
    """Helper function to check if the cached value from file is valid.

    Args:
        file: The Path object representing a file potentially containing
        previously cached value.
        days: Number of days after which the cached value becomes invalid.
        add_to_ignored: If force_refresh is set and this arg is set, the
        file is added to an ignored set of files so that this function doesn't
        return False for the same file if it is called again (this prevents
        refreshing the same cached value multiple times).

    Returns: True iff the cached value in file is valid.
    """
    MAX_DAYS_TO_FORCE_REFRESH = 40
    if (
        _ctx[_FORCE_STR]
        and days < MAX_DAYS_TO_FORCE_REFRESH
        and file.name not in _ctx[_FORCED_FILES_STR]
    ):
        # Ignore cached value.
        if add_to_ignored:
            _ctx[_FORCED_FILES_STR].add(file.name)
        return False
    return (file.exists() and get_file_age(file) < days)


def _call_func(class_obj, func):
    """Helper function to return value of class_obj.func().

    In addition to calling function, this helper also calls the
    cache_miss function if one is set in the context.

    Args:
        class_obj: The object of a particular class implementing Cacheable
        interface.
        func: The function whose return values has to be cached. Assumed
        to take no parameters.

    Returns: The return value of the func.
    """
    global _ctx
    if _MISS_FUNC_STR in _ctx:
        _ctx[_MISS_FUNC_STR]()
    return func(class_obj)


def _cache_filename(class_obj, func, days):
    """Returns the filename to be used for the args."""
    key = f'{func.__qualname__}_{class_obj.cache_key()}'
    return f'{days}_{md5(key.encode("utf8")).hexdigest()}.lkc'


def cache(days):
    """Returns decorator that caches functions return value on disk for
    specified number of days.

    Args:
        days: Number of days for which to cache the return value of the
        function.

    Returns: The decorator.
    """
    def decorator(func):
        @functools.wraps(func)
        def new_func(class_obj):
            global _ctx
            if _CACHE_STR not in _ctx:
                # Cache dir not set. Set to default.
                set_cache_dir(_DEFAULT_DIR)
            cache_dir = _ctx[_CACHE_STR]
            if not cache_dir:
                return _call_func(class_obj, func)

            file = cache_dir / _cache_filename(class_obj, func, days)
            if _valid_cached_value(file, days):
                return pickle.loads(file.read_bytes())
            value = _call_func(class_obj, func)
            file.write_bytes(pickle.dumps(value))
            return value
        new_func.cached_days = days
        return new_func
    return decorator


class _Prefetch:
    """Class to help with prefetching and caching of multiple values in
    parallel threads."""

    def __init__(self):
        self.cache_key_to_funcs = {}
        global _ctx
        if _CACHE_STR not in _ctx:
            # Cache dir not set. Set to default.
            set_cache_dir(_DEFAULT_DIR)
        self.cache_dir = _ctx[_CACHE_STR]

    def _return_cached_funcs(self, class_obj):
        all_methods = [getattr(class_obj, f) for f in dir(class_obj)]
        return [f for f in all_methods if callable(f)
                and hasattr(f, 'cached_days')]

    def add(self, class_obj):
        """Add class_obj to the list of objects whose cached methods are to be
        prefetched."""
        if not self.cache_dir:
            # Caching is disabled, don't prefetch.
            return

        cache_key = class_obj.cache_key()
        if self.cache_key_to_funcs.get(cache_key) is not None:
            # Already added to be prefetched.
            return

        funcs_to_refresh = []
        for func in self._return_cached_funcs(class_obj):
            file = self.cache_dir / _cache_filename(
                class_obj, func, func.cached_days)
            if not _valid_cached_value(file, func.cached_days,
                                       add_to_ignored=False):
                funcs_to_refresh.append(func)

        self.cache_key_to_funcs[cache_key] = funcs_to_refresh

    def fetch(self):
        """Fetch all cached methods of objects added earlier via add() call
        in parallel threads."""
        def prefetch_fn(funcs):
            for f in funcs:
                f()

        global _ctx
        # Reset cache miss func to None so it is not called from multiple
        # threads in parallel.
        cache_miss_func = None
        if _MISS_FUNC_STR in _ctx:
            cache_miss_func = _ctx[_MISS_FUNC_STR]
            set_cache_miss_func(None)

        fs = []
        with concurrent.futures.ThreadPoolExecutor() as executor:
            fs = [executor.submit(prefetch_fn, func_list) for func_list in
                  self.cache_key_to_funcs.values()]
            while len(fs) != 0:
                fs = concurrent.futures.wait(fs, timeout=0.1).not_done
                if cache_miss_func:
                    cache_miss_func()

        # Reset the map, so it can be optionally used again with add() method.
        self.cache_key_to_funcs = {}
        # Restore cache miss funcion.
        set_cache_miss_func(cache_miss_func)


# Global object of type Prefetch used for prefetching cached functions using
# parallel threads.
_prefetch_obj = None


def prefetch_add(class_obj):
    """Add class_obj to list of objects who cached methods are to be
    prefetched."""
    global _prefetch_obj
    if _prefetch_obj is None:
        _prefetch_obj = _Prefetch()
    _prefetch_obj.add(class_obj)


def prefetch():
    """Fetch all cached methods of objects added earlier via the prefetch_add()
    call in parallel threads."""
    assert _prefetch_obj is not None, (
        'prefetch_add must be called before calling prefetch')
    _prefetch_obj.fetch()
