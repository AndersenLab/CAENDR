import os
from logzero import logger

from google.cloud import datastore

from caendr.models.datastore import Container, Entity
from caendr.services.cloud.datastore import get_ds_entity



class JobEntity(Entity):

  # Map from JobEntity container fields -> Container fields
  # Props listed here will be converted to JobEntity object properties,
  # and will use the JobEntity.__container object as their source of truth.
  __container_prop_map = {
    'container_repo':     'repo',
    'container_name':     'container_name',
    # 'container_registry': 'container_registry',
    'container_version':  'container_tag',
  }


  ## Initialization ##

  def __new__(cls, *args, **kwargs):
    if cls is JobEntity:
      raise TypeError(f"Class '{cls.__name__}' should never be instantiated directly -- subclasses should be used instead.")
    return super(JobEntity, cls).__new__(cls)


  def __init__(self, *args, **kwargs):

    # Create Container object to store relevant Container fields
    self.__container = Container()

    # Initialize from superclass
    super(JobEntity, self).__init__(*args, **kwargs)

    self._init_container(*args, **kwargs)
    self.set_properties(**kwargs)


  def _init_container(self, *args, **kwargs):
    '''
      Initialize this JobEntity's source Container object.
      Accepts *args and **kwargs from __init__.
    '''

    # Copying an existing Entity object
    if len(args) > 0 and type(args[0]) == datastore.entity.Entity:
      self._set_container_props_from(args[0])

    # Downloading an existing Entity from datastore
    elif self._exists:
      item = get_ds_entity(self.kind, args[0])
      self._set_container_props_from(item)



  ## Properties List ##

  @classmethod
  def get_props_set(cls):
    return {
      *super(JobEntity, cls).get_props_set(),
      'container_repo',
      'container_name',
      'container_version',
    }


  def __iter__(self):
    '''
      Convert entity to an iterable.  Yields all fields from superclass(es), then fields specific to self.
    '''
    yield from super(JobEntity, self).__iter__()
    yield from (
      ( k , self[k] ) for k in self.__container_prop_map if self[k] is not None
    )


  def __getitem__(self, prop):
    '''
      Make properties listed in props_set accessible with bracket notation.
      Properties that are not set will return as None.

      Container properties are taken from Container object.

      Raises:
        KeyError: prop not found in props_set
    '''

    # Forward container props to Container object
    if prop in self.__container_prop_map:
      return self.__container[ self.__container_prop_map[ prop ] ]

    # Handle non-container props with default lookup method
    return super(JobEntity, self).__getitem__(prop)



  ## Set Properties ##

  def set_properties(self, **kwargs):
    '''
      Pass Container properties to Container object.
    '''

    # Set non-container props through super method
    super(JobEntity, self).set_properties(**{
      k: v for k, v in kwargs.items() if k not in self.__container_prop_map
    })

    # Pass container props to Container
    self._set_container_props_from(kwargs)


  def _set_container_props_from(self, src):
    '''
      Set the Container object's properties from a source object.

      Properties must be accessible in the source via __getitem__ (i.e. bracket notation).
      Properties in the source must be named by the *keys* in IndelPrimer.__container_prop_map.
    '''
    self.__container.set_properties(**{
      container_field_name: src[indel_field_name]
        for indel_field_name, container_field_name in self.__container_prop_map.items()
        if indel_field_name in src
    })



  ## Container object ##

  def get_container(self) -> Container:
    ''' Get the Container for this object. '''
    return self.__container


  def set_container(self, c: Container):
    ''' Set the Container for this object. Implicitly sets all container fields. '''
    if type(c) != Container:
      raise TypeError()
    self.__container = c


  def container_equals(self, c: Container) -> bool:
    '''
      Check whether this object was generated in a given Container.

      TODO: Should this be equivalent to two Containers being equal (__eq__)?
            Currently ignores container registry, since existing Indel Primer
            results don't store that field.
    '''
    # Check whether repo + name + tag is the same for both Containers
    return type(c) == Container and self.__container.full_string() == c.full_string()



  ## Container properties ##

  # Make these explicitly properties of Indel Primer object so that getting/setting
  # redirects to Container object -- single source of truth

  @property
  def container_repo(self):
    return self.__container[ self.__container_prop_map['container_repo'] ]

  @container_repo.setter
  def container_repo(self, v):
    self.__container[ self.__container_prop_map['container_repo'] ] = v

  @property
  def container_name(self):
    return self.__container[ self.__container_prop_map['container_name'] ]

  @container_name.setter
  def container_name(self, v):
    self.__container[ self.__container_prop_map['container_name'] ] = v

  @property
  def container_version(self):
    return self.__container[ self.__container_prop_map['container_version'] ]

  @container_version.setter
  def container_version(self, v):
    self.__container[ self.__container_prop_map['container_version'] ] = v
