from abc import ABC, abstractmethod
from datetime import datetime
import functools
from hashlib import md5
from pathlib import Path
import pickle

# Inspired by https://pypi.org/project/cache-to-disk/. I tried using other
# options such as requests-cache, but it was too slow compared to the solution
# implemented here.
# TODO(sarvjeets): It would be good to get rid of this one-off solution and switch
# to something more standard.


class Cacheable(ABC):
    @abstractmethod
    def cache_key(self):
        """Unique string value used as key for caching."""
        pass


def get_file_age(file):
    return (datetime.today() -
            datetime.fromtimestamp(file.stat().st_mtime)).days


# Dict to keep cache context.
# cache_dir:
# The pathlib.Path object specifying cache directory. If set to None,
# caching is disabled. Default: ~/.lakshmicache
# force_refresh:
# If set to True, new values are generated even if a cached one is
# available.
_ctx = {'force_refresh': False}
_DEFAULT_DIR = Path.home() / '.lakshmicache'
_CACHE_STR = 'cache_dir'
_FORCE_STR = 'force_refresh'


def set_force_refresh(v):
    global _ctx
    _ctx[_FORCE_STR] = v


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


def cache(days):
    def decorator(func):
        @functools.wraps(func)
        def new_func(class_obj):
            global _ctx
            if _CACHE_STR not in _ctx.keys():
                # Cache dir not set. Set to default.
                set_cache_dir(_DEFAULT_DIR)
            cache_dir = _ctx[_CACHE_STR]
            if not cache_dir:
                return func(class_obj)
            force_refresh = _ctx[_FORCE_STR]

            key = f'{func.__qualname__}_{class_obj.cache_key()}'
            filename = f'{days}_{md5(key.encode("utf8")).hexdigest()}.lkc'
            file = cache_dir / filename

            if not force_refresh and file.exists() and get_file_age(file) < days:
                return pickle.loads(file.read_bytes())
            value = func(class_obj)
            file.write_bytes(pickle.dumps(value))
            return value
        return new_func
    return decorator
