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
    @abstractmethod
    def cache_key(self):
        """Unique string value used as key for caching."""
        pass


def get_file_age(file):
    return (datetime.today()
            - datetime.fromtimestamp(file.stat().st_mtime)).days


# Constants.
_DEFAULT_DIR = Path.home() / '.lakshmicache'
_CACHE_STR = 'cache_dir'
_FORCE_STR = 'force_refresh'
_MISS_FUNC_STR = 'miss_func'

# Dict to keep cache context.
# cache_dir:
# The pathlib.Path object specifying cache directory. If set to None,
# caching is disabled. Default: ~/.lakshmicache
# force_refresh:
# If set to True, new values are generated even if a cached one is
# available.
# miss_func:
# If set, this function is called for every cache miss.
_ctx = {_FORCE_STR: False}


def set_force_refresh(v):
    global _ctx
    _ctx[_FORCE_STR] = v


def set_cache_miss_func(f):
    global _ctx
    if f:
        _ctx[_MISS_FUNC_STR] = f
    else:
        _ctx.pop(_MISS_FUNC_STR, None)


def set_cache_dir(cache_dir):
    """Sets the cache directory.

    If the cache directory is not specific, default ~/.lakshmicache
    is used.

    Args:
        cache_dir: The pathlib.Path object specifying cache directory.
        If set to None, caching is disabled.
    """
    global _ctx
    _ctx[_CACHE_STR] = cache_dir
    if cache_dir is None:
        return
    cache_dir.mkdir(exist_ok=True)
    for file in cache_dir.glob('*_*.lkc'):
        days = int(file.name.split('_')[0])
        if get_file_age(file) >= days:
            file.unlink()


def call_func(class_obj, func):
    global _ctx
    if _MISS_FUNC_STR in _ctx:
        _ctx[_MISS_FUNC_STR]()
    return func(class_obj)


def cache(days):
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
