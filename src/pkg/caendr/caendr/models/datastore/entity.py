import json
from datetime import datetime, timezone

from google.cloud import datastore

from caendr.services.cloud.datastore import get_ds_entity, save_ds_entity, query_ds_entities



def _datetime_sort_key(datetime_or_none, set_none_max = False):
  '''
    Helper function for sorting Entities by a datetime field, allowing None entries.
    None entries are mapped to the minimum possible datetime value unless set_none_max
    is True, in which case they are mapped to the maximum possible datetime value.

    Best used as key in sorted().

    Args:
      datetime_or_none (datetime, None): A datetime object or None.
      set_none_max (bool): Whether to map None to datetime.min or datetime.max.

    Returns:
      (datetime): The key to use in sorting.
  '''
  if datetime_or_none is None:
    return datetime.max if set_none_max else datetime.min
  else:
    return datetime_or_none.replace(tzinfo = None)



class Entity(object):
  """
    Base model for datastore entity.

    Functions like a dictionary with a restricted set of possible keys, defined in get_props_set().
    Fields are get/setable with bracket notation, and return as None if not set.

    Supports iteration (and therefore dictionary conversion) -- will only expose prop fields,
    not internal attributes like `kind`.  In other words, all fields in the dict output will be
    saved to the datastore.  This is important for subclassing.

    Subclasses should override:
      - get_props_set() to add props to the class
      - kind to specify a unique kind of entity

    Generally, they may also want to override:
      - __set_item__() if properties must be parsed and/or stored specially (e.g. not in __dict__)
      - __get_item__() if properties must be retrieved in some unique way (e.g. not from __dict__)
      - _init_from_entity(), _init_from_datastore(), and/or save() if the class must interact with
          the datastore in some unique way
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
      elif v is not None:
        result_out[k] = v

    # Update properties
    self.set_properties(**result_out)
    self.set_properties_meta(**result_out)


  def _init_from_datastore(self, obj):
    '''
      Initialize by copying fields from an object downloaded from the datastore.
      Can be overwritten by subclasses if special functionality is needed.
    '''
    self._exists = True
    self.set_properties(**obj)
    self.set_properties_meta(**obj)


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
    '''
      Define the set of possible keys for an entity.

      This set should be extended in subclasses.
    '''
    return {}

  @classmethod
  def get_props_set_meta(cls):
    '''
      Define the set of metadata properties for an entity.

      These are set automatically when saving/retrieving an Entity,
      and should not be set directly.
    '''
    return {
      'created_on',
      'modified_on',
    }



  ## Get Properties ##

  def __getitem__(self, prop):
    '''
      Make properties listed in props_set accessible with bracket notation.
      Properties that are not set will return as None.

      Raises:
        KeyError: prop not found in props_set
    '''
    if prop in self.__class__.get_props_set():
      return getattr(self, prop, None)
    else:
      raise KeyError(f'Could not get property "{prop}": not defined in property set.')


  def __iter__(self):
    '''
      Iterate through all props in the entity.

      Returns all attributes saved in this object's __dict__ field, with keys
      present in the props set.

      Does not return attributes such as `kind` or `name`, as these are not
      meant to be stored directly as fields in the datastore.

      Uses __getitem__ to retrieve props. Subclasses should only override this
      function if they add props which cannot be retrieved normally through
      __getitem__.
    '''
    props = self.get_props_set()
    return ( (k, self[k]) for k in props if self[k] is not None )



  ## Set Properties ##

  def __setitem__(self, prop, val):
    '''
      Make properties listed in props_set set-able with bracket notation.

      Raises:
        KeyError: prop not found in props_set
    '''
    if prop in self.__class__.get_props_set():
      setattr(self, prop, val)
    else:
      raise KeyError(f'Could not set property "{prop}": not defined in property set.')


  def set_properties(self, **kwargs):
    '''
      Set multiple properties using keyword arguments.

      Uses __setitem__ to set props. Subclasses should only override this
      function if they add props which cannot be set normally through
      __setitem__.
    '''
    props = self.get_props_set()
    for k, v in kwargs.items():
      if k in props:
        self[k] = v



  # Meta Properties ##

  def set_properties_meta(self, **kwargs):
    '''
      Copy the metadata properties from keyword args.
      See props listed in get_props_set_meta().
    '''
    props = self.get_props_set_meta()
    self.__dict__.update((k, v) for k, v in kwargs.items() if k in props)


  @property
  def created_on(self):
    return self.__dict__.get('created_on')


  @property
  def modified_on(self):
    return self.__dict__.get('modified_on')



  ## Sort Methods ##

  @classmethod
  def sort_by_created_date(cls, arr, reverse = False, set_none_max = False):
    return sorted( arr, key = lambda e: _datetime_sort_key(e.created_on, set_none_max=set_none_max), reverse=reverse )

  @classmethod
  def sort_by_modified_date(cls, arr, reverse = False, set_none_max = False):
    return sorted( arr, key = lambda e: _datetime_sort_key(e.modified_on, set_none_max=set_none_max), reverse=reverse )



  ## Querying ##

  @classmethod
  def query_ds(cls, *args, **kwargs):
    '''
      Query all datastore entities with this class's kind, and return as objects
      of this Entity subclass type.

      Should be called from subclasses, e.g. 'IndelPrimer.query_all( ... )'
      instead of 'Entity.query_all( ... )'.
    '''
    return [ cls(e) for e in query_ds_entities(cls.kind, *args, **kwargs) ]

