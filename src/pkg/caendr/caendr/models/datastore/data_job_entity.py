import os

from caendr.services.logger import logger

from caendr.models.datastore import JobEntity, UserOwnedEntity

from caendr.services.cloud.storage import check_blob_exists



MODULE_SITE_BUCKET_PRIVATE_NAME = os.environ.get('MODULE_SITE_BUCKET_PRIVATE_NAME')



class DataJobEntity(JobEntity, UserOwnedEntity):
  '''
    Subclass of Entity for user submitted pipeline jobs, associated with some data file(s).

    Should never be instantiated directly -- in fact, this is prevented in this class's __new__ function.
    Instead, specific job types should be subclasses of this class.
  '''

  # Datastore paths for data & results associated with a job type
  # Must be overridden in subclasses
  _blob_prefix = None
  _input_file  = None
  _result_file = None

  # Display name for reports of this type, used for human-readable messages & notifications
  _report_display_name = None


  ## Initialization ##

  def __new__(cls, *args, **kwargs):
    if cls is DataJobEntity:
      raise TypeError(f"Class '{cls.__name__}' should never be instantiated directly -- subclasses should be used instead.")
    return super(DataJobEntity, cls).__new__(cls)



  @classmethod
  def get_report_display_name(cls):
    if cls._report_display_name is None:
      raise NotImplementedError(f'Class {cls.__name__} must define a value for _report_display_name.')
    return cls._report_display_name



  ## Buckets & Paths ##

  @classmethod
  def get_bucket_name(cls):
    return MODULE_SITE_BUCKET_PRIVATE_NAME

  def get_blob_path(self):
    if self._blob_prefix is None:
      raise NotImplementedError(f'Class {self.__class__.__name__} must define a value for _blob_prefix.')
    else:
      return f'{self._blob_prefix}/{self.container_name}/{self.container_version}/{self.data_hash}'

  def get_data_blob_path(self):
    if self._input_file is None:
      raise NotImplementedError(f'Class {self.__class__.__name__} must define a value for _input_file.')
    else:
      return f'{self.get_blob_path()}/{self._input_file}'

  def get_result_blob_path(self):
    if self._result_file is None:
      raise NotImplementedError(f'Class {self.__class__.__name__} must define a value for _result_file.')
    else:
      return f'{self.get_blob_path()}/{self._result_file}'



  ## Properties List ##

  @classmethod
  def get_props_set_meta(cls):
    return {
      *super().get_props_set_meta(),
      'data_hash',
    }

  # Include data hash when iterating
  def __iter__(self):
    yield from super().__iter__()
    yield ('data_hash', self.data_hash)



  ## Meta props ##

  # Meta props are stored in self.__dict__ by default.

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



  ## Cache ##

  @classmethod
  def check_cached_submission(cls, data_hash, username, container, status=None):

    # Check for reports by this user with a matching data hash
    filters = [
      ('data_hash', '=', data_hash),
      ('username',  '=', username),
    ]

    # Convert status to iterable (set), if a single value passed
    if status is not None and not hasattr(status, '__iter__'):
      status = {status}

    # Loop through each matching report, sorted newest to oldest
    # Prefer a match with a date, if one exists
    for match in cls.sort_by_created_date( cls.query_ds(filters=filters), set_none_max=True ):

      # If containers match and status is correct, return the matching Entity
      if match.container_equals(container) and (status and match['status'] in status):
        return match


  def check_cached_result(self):
    return check_blob_exists(self.get_bucket_name(), self.get_result_blob_path())
