from time import time

from config import config
from caendr.services.cloud.datastore import delete_ds_entities_by_query
from caendr.models.cache import DatastoreCache

def datastore_cache(app, config, args, kwargs):
  key_prefix = config["CAENDR_VERSION"]
  return DatastoreCache(key_prefix, *args, **kwargs)

def delete_expired_cache():
  epoch_time = int(time())
  filters = [("expires", "<", epoch_time)]
  num_deleted = delete_ds_entities_by_query(DatastoreCache.kind, filters=filters, projection=['expires'])
  return num_deleted

