from caendr.services.logger import logger

from caendr.models.datastore import JobEntity, User

from caendr.services.cloud.storage import check_blob_exists
from caendr.utils.data import unique_id



class DataJobEntity(JobEntity):
  '''
    Subclass of Entity for user submitted pipeline jobs, associated with some data file(s).

    Should never be instantiated directly -- in fact, this is prevented in this class's __new__ function.
    Instead, specific job types should be subclasses of this class.
  '''


  ## Initialization ##

  def __new__(cls, *args, **kwargs):
    if cls is DataJobEntity:
      raise TypeError(f"Class '{cls.__name__}' should never be instantiated directly -- subclasses should be used instead.")
    return super(DataJobEntity, cls).__new__(cls)


  def __init__(self, name_or_obj = None, *args, **kwargs):

    # If nothing passed for name_or_obj, create a new ID to use for this object
    if name_or_obj is None:
      name_or_obj = unique_id()
      self.set_properties_meta(id = name_or_obj)

    # Initialize from superclass
    super().__init__(name_or_obj, *args, **kwargs)


  ## Properties List ##

  @classmethod
  def get_props_set(cls):
    return {
      *super().get_props_set(),
      'username',
    }

  @classmethod
  def get_props_set_meta(cls):
    return {
      *super().get_props_set_meta(),
      'id',
      'data_hash',
    }

  # Include data hash when iterating
  def __iter__(self):
    yield from super().__iter__()
    yield ('data_hash', self.data_hash)


  ## Meta props ##

  # Meta props are stored in self.__dict__ by default.

  @property
  def id(self):
    '''
      This Entity's unique ID.
      This field cannot be set manually; it must be determined at initialization.
    '''
    return self._get_meta_prop('id')

  @property
  def data_hash(self):
    '''
      A hash value generated from the data associated with this Entity.
    '''
    return self._get_meta_prop('data_hash')

  @data_hash.setter
  def data_hash(self, val):
    logger.debug(f'Setting data hash for Entity {self.id} to {val}.')
    self._set_meta_prop('data_hash', val)



  ## User Object ##

  def get_user(self) -> User:
    '''
      Look up the user associated with this submission.
    '''
    return User.get_ds(self['username'])

  # TODO: Should this use the user's 'username' prop instead?
  def set_user(self, user: User):
    '''
      Set user properties from a User object.
      By default, sets username to match provided user.
    '''
    self['username'] = user.name



  ## Cache ##

  @classmethod
  def check_cached_submission(cls, data_hash, username, container, status=None):

    # Check for reports by this user with a matching data hash
    filters = [
      ('data_hash', '=', data_hash),
      ('username',  '=', username),
    ]

    # If desired, filter by status as well
    if status:
      filters += [('status', '=', status)]

    # Loop through each matching report, sorted newest to oldest
    # Prefer a match with a date, if one exists
    for match in cls.sort_by_created_date( cls.query_ds(filters=filters), set_none_max=True ):

      # If containers match, return the matching Entity
      if match.container_equals(container):
        return match


  def check_cached_result(self):
    return check_blob_exists(self.get_bucket_name(), self.get_result_blob_path())
