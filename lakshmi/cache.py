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

import functools
import pickle
from abc import ABC, abstractmethod
from datetime import datetime
from hashlib import md5
from pathlib import Path

# Inspired by https://pypi.org/project/cache-to-disk/. I tried using other
# options such as requests-cache, but it was too slow compared to the solution
# implemented here.
# TODO(sarvjeets): It would be good to get rid of this one-off solution and
# switch to something more standard.


class Cacheable(ABC):
    """Interface that declares that a particular class's method return
    values could be cached. The methods should not take a parameter,
    and cache_key() + method name should uniquely imply the return
    value of that class."""
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
_MISS_FUNC_STR = 'miss_func'

# Dict (string -> object) to keep cache context.
# Description of keys to what is stored:
# _CACHE_STR:
# The pathlib.Path object specifying cache directory. If set to None,
# caching is disabled. Default: _DEFAULT_DIR
# _FORCE_STR:
# If set to True, new values are generated even if a cached one is
# available. Default: False
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


def set_cache_miss_func(f):
    """Sets the function to call for cache-misses.

    Args:
        f: The function to call whenever a cache-miss happens (i.e. whenever
        the underlying function is called instead of using a cached value).
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


def call_func(class_obj, func):
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
                return call_func(class_obj, func)
            force_refresh = _ctx[_FORCE_STR]

            key = f'{func.__qualname__}_{class_obj.cache_key()}'
            filename = f'{days}_{md5(key.encode("utf8")).hexdigest()}.lkc'
            file = cache_dir / filename

            if (
                not force_refresh
                and file.exists()
                and get_file_age(file) < days
            ):
                return pickle.loads(file.read_bytes())

            value = call_func(class_obj, func)
            file.write_bytes(pickle.dumps(value))
            return value
        return new_func
    return decorator
