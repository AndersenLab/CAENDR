from caendr.models.datastore import Container, Entity



class JobEntity(Entity):
  '''
    Subclass of Entity for pipeline jobs.

    Manages a private Container Entity instance to track container fields.

    Should never be instantiated directly -- in fact, this is prevented in this class's __new__ function.
    Instead, specific job types should be subclasses of this class.
  '''


  # Map from JobEntity container fields -> Container fields
  # Props listed here will be converted to JobEntity object properties,
  # and will use the JobEntity.__container object as their source of truth.
  __container_prop_map = {
    'container_repo':     'repo',
    'container_name':     'container_name',
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
      Convert entity to an iterable.

      Container fields are not stored in this object's __dict__, so they must be
      accessed separately.
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
      return self.__container.__getitem__( self.__container_prop_map[ prop ] )

    # Handle non-container props with default lookup method
    return super(JobEntity, self).__getitem__(prop)



  ## Set Properties ##


  def __setitem__(self, prop, val):
    '''
      Make properties listed in props_set set-able with bracket notation.

      Raises:
        KeyError: prop not found in props_set
    '''

    # Forward container props to Container object
    if prop in self.__container_prop_map:
      return self.__container.__setitem__( self.__container_prop_map[ prop ], val )

    # Handle non-container props with default lookup method
    return super(JobEntity, self).__setitem__( prop, val )


  def set_properties(self, **kwargs):
    '''
      Set object properties, passing Container properties to Container object.

      Container properties in the source must be named by the *keys* in JobEntity.__container_prop_map.
    '''

    # Set non-container props through super method
    super(JobEntity, self).set_properties(**{
      k: v for k, v in kwargs.items() if k not in self.__container_prop_map
    })

    # Pass container props to Container
    self.__container.set_properties(**{
      container_field_name: kwargs[job_field_name]
        for job_field_name, container_field_name in self.__container_prop_map.items()
        if job_field_name in kwargs
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
            Currently ignores container registry, since existing JobEntity
            results don't store that field.
    '''
    # Check whether repo + name + tag is the same for both Containers
    return type(c) == Container and self.__container.full_string() == c.full_string()



  ## Container properties ##

  # Make these explicitly properties of JobEntity object so that getting/setting
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
