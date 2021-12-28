import pickle
import base64

from cachelib import BaseCache
from time import time

from caendr.services.cloud.datastore import get_ds_entity, save_ds_entity

class DatastoreCache(BaseCache):

  kind = 'cache'

  def __init__(self, key_prefix, default_timeout=500):
    BaseCache.__init__(self, default_timeout)
    self.key_prefix = key_prefix

  def set(self, key, value, timeout=None):
    expires = time() + timeout
    try:
      value = base64.b64encode(pickle.dumps(value))
      save_ds_entity(self.kind, self.key_prefix + "/" + key, value=value, expires=expires, exclude_from_indexes=['value'])
      return True
    except:
      return False

  def get(self, key):
    try:
      item = get_ds_entity(self.kind, self.key_prefix + "/" + key)
      value = item.get('value')
      value = pickle.loads(base64.b64decode(value))
      expires = item.get('expires')
      if expires == 0 or expires > time():
        return value
    except AttributeError:
      return None

  def get_many(self, *keys):
    return [self.get(key) for key in keys]

  def get_dict(self, *keys):
    results = {}
    for key in keys:
      try:
        results.update({key: get_ds_entity(self.kind, key)})
      except AttributeError:
        pass
    return results

  def has(self, key):
    try:
      item = get_ds_entity(self.kind, key)
      expires = item.get('expires')
      if expires == 0 or expires > time():
        return True
    except:
      return False

  def set_many(self, mapping, timeout):
    for k, v in mapping.items():
      save_ds_entity(self.kind, k, value=v)

