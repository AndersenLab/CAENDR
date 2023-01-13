import json
from datetime import datetime, timezone

from google.cloud import datastore

from caendr.services.cloud.datastore import get_ds_entity, save_ds_entity



class Entity(object):
  """
    Base model for datastore entity.

    Functions like a dictionary with a restricted set of possible keys, defined in get_props_set().
    Fields are get/setable with bracket notation, and return as None if not set.

    Supports iteration (and therefore dictionary conversion) -- will only expose prop fields,
    not internal attributes like `kind`.  In other words, all fields in the dict output will be
    saved to the datastore.  This is important for subclassing.
  """

  # Default kind for the entity
  # This should be overwritten by subclasses
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


  def __repr__(self):
    return f"<{self.kind}:{getattr(self, 'name', 'no-name')}>"



  ## Saving to Datastore ##

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

    # Combine props dict with meta properties defined above
    props = { **dict(self), **meta_props }

    # Save the entity in datastore
    save_ds_entity(self.kind, self.name, **props)



  ## Properties List ##

  @classmethod
  def get_props_set(cls):
    return {}


  def __iter__(self):
    '''
      Iterate through all props in the entity.

      Returns all attributes saved in this object's __dict__ field, with keys
      present in the props set.

      Does not return attributes such as `kind` or `name`, as these are not
      meant to be stored directly as fields in the datastore.

      If subclasses add entity fields that are not stored in __dict__, they
      should override this function to include those fields in the resulting
      generator.
    '''
    props = self.get_props_set()
    return ( (k, v) for k, v in self.__dict__.items() if k in props )


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


  def __setitem__(self, prop, val):
    '''
      Make properties listed in props_set set-able with bracket notation.

      Raises:
        KeyError: prop not found in props_set
    '''
    if prop in self.__class__.get_props_set():
      return self.__dict__.__setitem__(prop, val)
    raise KeyError()


  def set_properties(self, **kwargs):
    '''
      Set multiple properties using keyword arguments.
    '''
    props = self.get_props_set()
    self.__dict__.update((k, v) for k, v in kwargs.items() if k in props)

