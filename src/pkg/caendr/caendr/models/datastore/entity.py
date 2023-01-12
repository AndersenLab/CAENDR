import json
from datetime import datetime, timezone

from google.cloud import datastore

from caendr.services.cloud.datastore import get_ds_entity, save_ds_entity

class Entity(object):
  """  Base model for datastore entity """
  kind = "Entity"

  def __init__(self, name_or_obj=None):
    """
      Args:
        name_or_obj - A name for a new datastore item or an existing one to retrieve from the datastore               
    """
    self.exclude_from_indexes = None
    self._exists = False

    if type(name_or_obj) == datastore.entity.Entity:
      # Parse JSON fields when instantiating without loading from gcloud.
      result_out = {}
      for k, v in name_or_obj.items():
        if isinstance(v, str) and v.startswith("JSON:"):
          result_out[k] = json.loads(v[5:])
        elif v:
          result_out[k] = v
      self.__dict__.update(result_out)
      self.kind = name_or_obj.key.kind
      self.name = name_or_obj.key.name
    elif name_or_obj:
      self.name = name_or_obj
      item = get_ds_entity(self.kind, name_or_obj)
      if item:
        self._exists = True
        self.__dict__.update(item)


  def save(self):
    ''' Append metadata to the Entity and save it to the datastore'''
    now = datetime.now(timezone.utc)
    meta_props = {}

    # Update timestamps
    if not self._exists:
      meta_props['created_on'] = now
    meta_props.update({'modified_on': now})

    # Get list of props by converting to dict and excluding certain class vars
    props = { k: v for k, v in dict(self).items() if k not in ['kind', 'name'] }
    props.update(meta_props)

    # Save the entity in datastore
    save_ds_entity(self.kind, self.name, **props)


  def set_properties(self, **kwargs):
    props = self.get_props_set()
    self.__dict__.update((k, v) for k, v in kwargs.items() if k in props)


  @classmethod
  def get_props_set(cls):
    return {}


  def __iter__(self):
    '''
      Iterate through all props in the entity.
    '''
    return ( (k, v) for k, v in self.__dict__.items() if not k.startswith("_") )


  def __getitem__(self, prop):
    '''
      Make properties listed in props_set accessible with bracket notation.
      Properties that are not set will return as None.

      Raises:
        KeyError: prop not found in props_set
    '''
    if prop in self.__class__.get_props_set():
      return self.__dict__.get(prop)
    raise KeyError()


  def __repr__(self):
    if hasattr(self, 'name'):
      return f"<{self.kind}:{self.name}>"
    else:
      return f"<{self.kind}:no-name>"
