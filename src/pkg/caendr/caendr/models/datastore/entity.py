import json
from datetime import datetime, timezone

from google.cloud import datastore
from caendr.services.logger import logger

from caendr.models.error import NonUniqueEntity, NotFoundError
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

  def __init__(self, name_or_obj = None, safe = False, **kwargs):
    """
      Args:
        name_or_obj - A name for a new datastore item or an existing one to retrieve from the datastore               
    """
    self.exclude_from_indexes = None
    self._exists = False

    # If a datastore entity was passed, copy its fields
    if type(name_or_obj) == datastore.entity.Entity:
      self._init_from_entity(name_or_obj, safe=safe)

    # If a name was passed, check if the name already exists in the datastore
    elif name_or_obj:
      self.name = name_or_obj
      item = get_ds_entity(self.kind, name_or_obj)
      if item:
        self._init_from_datastore(item, safe=safe)

    # Catch any remaining keyword arguments and use them to initialize the object
    self.set_properties(**kwargs)


  def _init_from_entity(self, obj, safe=False):
    '''
      Copy constructor helper function.

      Initialize by copying a datastore entity that already exists locally.
      Can be overwritten by subclasses if special functionality is needed.
    '''

    # Set kind and name from object
    self.kind = obj.key.kind
    self.name = obj.key.name

    # Parse JSON fields when instantiating without loading from gcloud.
    result_out = Entity._parse_entity_to_dict(obj)

    # Update properties
    if safe:
      self.set_properties_safe(**result_out)
    else:
      self.set_properties(**result_out)
    self.set_properties_meta(**result_out)


  def _init_from_datastore(self, obj, safe=False):
    '''
      Initialize by copying fields from an object downloaded from the datastore.
      Can be overwritten by subclasses if special functionality is needed.
    '''
    self._exists = True
    if safe:
      self.set_properties_safe(**obj)
    else:
      self.set_properties(**obj)
    self.set_properties_meta(**obj)


  @classmethod
  def _parse_entity_to_dict(cls, obj):
    '''
      Parse JSON fields in an object.  Reads strings beginning with "JSON:" as JSON objects.
    '''
    return {
      k: json.loads(v[5:]) if isinstance(v, str) and v.startswith("JSON:") else v
        for k, v in obj.items()
    }


  def __repr__(self):
    '''
      String representation of the Entity. Displays kind and name/ID.
    '''

    # Subclasses that define an ID field should use that as their display name
    if ('id' in self.get_props_set()):
      return f"<{self.kind}:{getattr(self, 'id', 'no-id')}>"

    # Otherwise, try using the name field
    else:
      return f"<{self.kind}:{getattr(self, 'name', 'no-name')}>"



  ## Saving to Datastore ##

  def save(self):
    '''
      Append metadata to the Entity and save it to the datastore.
    '''
    now = datetime.now(timezone.utc)

    # Get dict of all meta properties
    meta_props = {
      prop: getattr(self, prop) for prop in self.get_props_set_meta()
    }

    # Update timestamps
    if not self._exists:
      meta_props['created_on'] = now
    meta_props['modified_on'] = now

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
      try:
        if type(val) == datastore.entity.Entity:
          setattr(self, prop, Entity._parse_entity_to_dict(val))
        else:
          setattr(self, prop, val)
      except Exception as ex:
        logger.error(f"Error setting {self.__class__.__name__}['{prop}'] = {val}")
        raise ex
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

  def set_properties_safe(self, **kwargs):
    props = self.get_props_set()
    for k, v in kwargs.items():
      if k in props:
        try:
          self[k] = v
        except Exception as ex:
          logger.warning(f"Error setting {self.__class__.__name__}['{k}'] = {v}")



  # Meta Properties ##

  def set_properties_meta(self, **kwargs):
    '''
      Copy the metadata properties from keyword args.
      See props listed in get_props_set_meta().
    '''
    props = self.get_props_set_meta()
    self.__dict__.update((k, v) for k, v in kwargs.items() if k in props)


  def _get_meta_prop(self, key, fallback=None):
    return self.__dict__.get(key, fallback)

  def _set_meta_prop(self, key, val):
    self.__dict__[key] = val


  @property
  def created_on(self):
    return self.__dict__.get('created_on')


  @property
  def modified_on(self):
    return self.__dict__.get('modified_on')



  ## Sort Methods ##

  @classmethod
  def sort_by_created_date(cls, arr, reverse = False, set_none_max = False):
    '''
      Sort a list of Entities by their creation date, with special handling for Entities that have no recorded creation date.
      By default, sorts oldest to newest.
    '''
    return sorted( arr, key = lambda e: _datetime_sort_key(e.created_on if e else None, set_none_max=set_none_max), reverse=reverse )

  @classmethod
  def sort_by_modified_date(cls, arr, reverse = False, set_none_max = False):
    '''
      Sort a list of Entities by the date they were last modified, with special handling for Entities that have no
      recorded modified date.
      By default, sorts oldest to newest.
    '''
    return sorted( arr, key = lambda e: _datetime_sort_key(e.modified_on if e else None, set_none_max=set_none_max), reverse=reverse )



  ## Querying ##

  @classmethod
  def query_ds(cls, safe=False, ignore_errs=False, *args, **kwargs):
    '''
      Query all datastore entities with this class's kind, and return as objects
      of this Entity subclass type.

      If `safe` is set to True, uses the safe version of the Entity class constructor. See __init__ for details.
      Overrides `ignore_errs`.

      If `ignore_errs` is set to True, filters out any matching Entities that threw an error while constructing.

      Should be called from subclasses, e.g. 'IndelPrimer.query_all( ... )'
      instead of 'Entity.query_all( ... )'.
    '''
    def construct_safe(e):
      try:
        return cls(e, safe=safe)
      except:
        return None

    if ignore_errs:
      matches = [ construct_safe(e) for e in query_ds_entities(cls.kind, *args, **kwargs) ]
      return [ e for e in matches if e is not None ]

    else:
      return [ cls(e, safe=safe) for e in query_ds_entities(cls.kind, *args, **kwargs) ]


  @classmethod
  def query_ds_unique(cls, key, val, required=False, safe=False):
    '''
      Query the datastore for a single unique entity where the `key` property is set to `val`.

      If `required` is set to True, will raise an error if no such entity is found; otherwise returns None.
      If multiple entities match the query, raises a NonUniqueEntity error with all matches in the `matches` field.

      If `safe` is set to True, uses the safe version of the Entity class constructor. See __init__ for details.
    '''

    # Run query with given key and val
    matches = cls.query_ds(safe=safe, filters=[(key, '=', val)])

    # If no matching entities found, return None
    if len(matches) == 0:
      if required:
        raise NotFoundError( cls.kind, {key: val} )
      else:
        return None

    # If exactly one entity found, return it
    elif len(matches) == 1:
      return matches[0]

    # If more than one entity found, raise an error
    else:
      raise NonUniqueEntity( cls.kind, key, val, matches )



  @classmethod
  def get_ds(cls, name, safe=False):
    '''
      Get the Entity from datastore with the matching name.
    '''

    # Ensure this is being run on a subclass of Entity, not Entity itself
    if cls is Entity:
      raise TypeError(f'Cannot run method "get_ds" on {cls.__name__}. Please run with subclass instead.')

    # Query datastore using this class's kind and the provided name
    match = get_ds_entity(cls.kind, name)

    # If a match was found, initialize an Entity object from it
    if match is not None:
      return cls(name, safe=safe)
