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
      # Entity fields
      *super(JobEntity, cls).get_props_set(),

      # Container fields
      'container_repo',
      'container_name',
      'container_version',

      # Other fields
      'operation_name',
      'status',
    }



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
