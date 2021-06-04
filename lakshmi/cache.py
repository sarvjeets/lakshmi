from abc import ABC, abstractmethod
from datetime import datetime
import functools
import os
import pickle

# Inspired by https://pypi.org/project/cache-to-disk/

# If this is None, caching is disabled.
CACHE_DIR = os.path.join(os.getcwd(), '.lakshmicache')

class Cacheable(ABC):
  @abstractmethod
  def CacheKey(self):
    """Unique string value used as key for caching."""
    pass

def get_file_age(filename):
  return (datetime.today() -
          datetime.fromtimestamp(os.path.getmtime(filename))).days

def cache(days):
  def decorator(func):
    @functools.wraps(func)
    def new_func(class_obj):
      if CACHE_DIR is None:
        return func(class_obj)

      if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR)

      key = '{}_{}_{}.pkl'.format(days,
                                  func.__qualname__,
                                  class_obj.CacheKey())
      filename = os.path.join(CACHE_DIR, key)

      if os.path.exists(filename):
        if get_file_age(filename) < days:
          with open(filename, 'rb') as f:
            return pickle.load(f)

      value = func(class_obj)
      with open(filename, 'wb') as f:
        pickle.dump(value, f)
      return value
    return new_func
  return decorator

def delete_old_cache():
  if CACHE_DIR is None or not os.path.exists(CACHE_DIR):
    return
  for file in os.listdir(CACHE_DIR):
    days = int(file.split('_')[0])
    if not file.endswith('.pkl'):
      raise Exception(
        'Unknown file {} in cache directory {}'.format(file, CACHE_DIR))
    full_filename = os.path.join(CACHE_DIR, file)
    if get_file_age(full_filename) >= days:
      os.remove(full_filename)

delete_old_cache()
