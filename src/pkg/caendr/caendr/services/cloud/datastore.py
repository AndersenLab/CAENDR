import json
from logzero import logger
from caendr.utils.json import dump_json

from google.cloud import datastore

dsClient = datastore.Client()

def delete_ds_entity_by_ref(kind, id):
  key = dsClient.key(kind, id)
  dsClient.delete(key)


def get_ds_entity(kind, name):
  ''' Returns item by kind and name from google datastore '''
  result = dsClient.get(dsClient.key(kind, name))
  logger.debug(f"get: {kind} - {name}")
  try:
    result_out = {'_exists': True}
    for k, v in result.items():
      if isinstance(v, str) and v.startswith("JSON:"):
        result_out[k] = json.loads(v[5:])
      elif v:
        result_out[k] = v

    return result_out
  except AttributeError:
    return None


def save_ds_entity(kind, name, **kwargs):
  ''' Saves an entity to the datastore, optionally preventing indexing of select properties '''
  try:
    exclude = kwargs.pop('exclude_from_indexes')
  except KeyError:
    exclude = False

  if exclude:
    m = datastore.Entity(key=dsClient.key(kind, name), exclude_from_indexes=exclude)
  else:
    m = datastore.Entity(key=dsClient.key(kind, name))

  for key, value in kwargs.items():
    if isinstance(value, dict):
      m[key] = 'JSON:' + dump_json(value)
    else:
      m[key] = value

  logger.debug(f"store: {kind} - {name}")
  dsClient.put(m)


def query_ds_entities(kind, filters=None, projection=(), order=None, limit=None, keys_only=False):
  ''' Queries the datastore for Entities of type 'kind' with optional filter and query parameters. 
      Filter example: [("var_name", "=", 1)]
  '''
  query = dsClient.query(kind=kind, projection=projection)
  if keys_only:
    query.keys_only()
  if order:
    query.order = order
  if filters:
    for var, op, val in filters:
      query.add_filter(var, op, val)
  if limit:
    return query.fetch(limit=limit)
  else:
    results = list(query.fetch())
    return results


def delete_ds_entities_by_query(kind, filters=None, projection=()):
    """
        Deletes all entities that are returned by a query. 
        Entities are deleted in page-sized batches as the results are being returned
        Returns the number of items deleted
    """
    # filters:
    # [("var_name", "=", 1)]
    query = dsClient.query(kind=kind, projection=projection)
    deleted_items = 0
    if filters:
      for var, op, val in filters:
        query.add_filter(var, op, val)

    iter = query.fetch()
    if iter.num_results == 0:
      return 0

    while True:
      entities, more, cursor = iter.next_page()
      keys = []
      for entity in entities:
        keys.append(entity.key)
      dsClient.delete_multi(keys)
      deleted_items += len(keys)
      if more is False:
        break
    return deleted_items


