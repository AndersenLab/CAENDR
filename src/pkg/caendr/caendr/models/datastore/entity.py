import json
from datetime import datetime, timezone

from google.cloud import datastore

from caendr.services.cloud.datastore import get_ds_entity, save_ds_entity

class Entity(object):
  """  Base model for datastore entity """
  kind = "Entity"


  ## Initialization ##

  def __init__(self, name_or_obj = None, **kwargs):
    """
      Args:
        name_or_obj - A name for a new datastore item or an existing one to retrieve from the datastore               
    """
    self.exclude_from_indexes = None
    self._exists = False

    # If a datastore entity was passed, copy its fields
    if type(name_or_obj) == datastore.entity.Entity:
      self._init_from_entity(name_or_obj)

    # If a name was passed, check if the name already exists in the datastore
    elif name_or_obj:
      self.name = name_or_obj
      item = get_ds_entity(self.kind, name_or_obj)
      if item:
        self._init_from_datastore(item)

    # Catch any remaining keyword arguments and use them to initialize the object
    self.set_properties(**kwargs)


  def _init_from_entity(self, obj):
    '''
      Copy constructor helper function.

      Initialize by copying a datastore entity that already exists locally.
      Can be overwritten by subclasses if special functionality is needed.
    '''

    # Set kind and name from object
    self.kind = obj.key.kind
    self.name = obj.key.name

    # Parse JSON fields when instantiating without loading from gcloud.
    result_out = {}
    for k, v in obj.items():
      if isinstance(v, str) and v.startswith("JSON:"):
        result_out[k] = json.loads(v[5:])
      elif v:
        result_out[k] = v

    # Update properties
    self.set_properties(**result_out)


  def _init_from_datastore(self, obj):
    '''
      Initialize by copying fields from an object downloaded from the datastore.
      Can be overwritten by subclasses if special functionality is needed.
    '''
    self._exists = True
    self.set_properties(**obj)


  def save(self):
    '''
      Append metadata to the Entity and save it to the datastore.
    '''
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



  ## Properties List ##

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



  ## Set Properties ##

  def set_properties(self, **kwargs):
    props = self.get_props_set()
    self.__dict__.update((k, v) for k, v in kwargs.items() if k in props)


  def __repr__(self):
    if hasattr(self, 'name'):
      return f"<{self.kind}:{self.name}>"
    else:
      return f"<{self.kind}:no-name>"
