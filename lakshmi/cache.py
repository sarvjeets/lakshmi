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

# If this is None, caching is disabled. Default is ~/.lakshmicache
_CACHE_DIR = None
# If True, cached entries are refreshed.
FORCE_REFRESH = False

def get_file_age(file):
  return (datetime.today() -
          datetime.fromtimestamp(file.stat().st_mtime)).days

def set_cache_dir(cache_dir):
  global _CACHE_DIR
  _CACHE_DIR = cache_dir
  if not _CACHE_DIR:
    return
  _CACHE_DIR.mkdir(exist_ok=True)
  for file in _CACHE_DIR.iterdir():
    if not file.name.endswith('.lkc'):
      raise Exception(
        'Unknown file {} in cache directory.'.format(file))
    days = int(file.name.split('_')[0])
    if get_file_age(file) >= days:
      file.unlink()

set_cache_dir(Path.home() / '.lakshmicache')

class Cacheable(ABC):
  @abstractmethod
  def CacheKey(self):
    """Unique string value used as key for caching."""
    pass


def cache(days):
  def decorator(func):
    @functools.wraps(func)
    def new_func(class_obj):
      if not _CACHE_DIR:
        return func(class_obj)

      key = md5('{}_{}'.format(
        func.__qualname__,
        class_obj.CacheKey()).encode('utf8')).hexdigest()
      filename = '{}_{}.lkc'.format(days, key)
      file = _CACHE_DIR / filename

      if not FORCE_REFRESH and file.exists() and get_file_age(file) < days:
        return pickle.loads(file.read_bytes())

      value = func(class_obj)
      file.write_bytes(pickle.dumps(value))
      return value
    return new_func
  return decorator
