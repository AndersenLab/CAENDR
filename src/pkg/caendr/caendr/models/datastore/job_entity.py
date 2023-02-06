from caendr.services.logger import logger

from caendr.models.datastore import Container, Entity
from caendr.models.error import CachedDataError, DuplicateDataError

from caendr.services.cloud.storage import check_blob_exists



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
    super().__init__(*args, **kwargs)



  ## Properties List ##

  @classmethod
  def get_props_set(cls):
    return {
      # Entity fields
      *super().get_props_set(),

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
    return type(c) == Container and self.__container.uri() == c.uri()



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



  ## Cache ##

  @classmethod
  def check_cache(cls, data_hash, username, container, status = None):

    # Check for reports with a matching data hash & container version
    filters = [
      ('data_hash',         '=', data_hash),
      ('container_version', '=', container.container_tag),
    ]

    # If desired, filter by status as well
    if status:
      filters += [('status', '=', status)]

    # Loop through each matching report
    for report in cls.query_ds(filters=filters):

      # If same job submitted by this user, return Duplicate Data Error
      if report.username == username:
        raise DuplicateDataError(report)

      # If same job submitted by a different user, return Cached Data Error
      else:
        raise CachedDataError(report)


  @classmethod
  def check_cached_submission(cls, data_hash, username, container):
    matches = cls.query_ds(filters=[('data_hash', '=', data_hash)])
    if len(matches) > 0:
      if matches[0].username == username and matches[0].container_equals(container):
        return matches[0]

    return None


  def check_cached_result(self):
    return check_blob_exists(self.get_bucket_name(), self.get_result_blob_path())
