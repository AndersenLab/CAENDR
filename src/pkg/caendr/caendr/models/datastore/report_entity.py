# Built-ins
from abc import abstractmethod
from enum import Enum
from typing import Union

# Parent class
from caendr.models.report    import GCPReport
from caendr.models.datastore import JobEntity, UserOwnedEntity

# Models
from caendr.models.status    import JobStatus
from caendr.models.datastore import Container, User

# Services
from caendr.services.cloud.storage import check_blob_exists



class ReportEntity(JobEntity, UserOwnedEntity, GCPReport):
  '''
    Stores metadata in a Datastore Entity.
    Manages an entity (metadata) and paths for input/output data

    An Entity subclass that fulfills the Report template class, making it directly usable as a Report in the Job Pipeline.

    Note that the abstract base class GCPReport comes last in the parent class list.
    This appears to be necessary for the method definitions in the Entity classes
    to override the abstract methods from GCPReport correctly.
  '''

  #
  # Kind
  #

  @classmethod
  def get_kind(cls):
    return cls.kind


  #
  # Instantiation
  # Route the GCPReport's create & lookup methods to the appropriate Entity methods
  #

  @classmethod
  def create(cls, **kwargs):
    return cls(**kwargs)

  @classmethod
  def lookup(cls, report_id: str):
    return cls.get_ds(report_id, silent = False)


  #
  # Data ID
  # Subclass can designate a property field to use as the data ID
  #

  # The report field to use as the data ID
  # Subclass should overwrite this abstract property,
  # then the chosen prop value will be accessible through the getter below
  @property
  @abstractmethod
  def _data_id_field(self) -> str:
    pass

  # Get the data ID field value, converting enums to their name values if desired
  def get_data_id(self, as_str=False):
    data_id = getattr( self, self._data_id_field )
    if as_str and isinstance(data_id, Enum):
      data_id = data_id.name
    return data_id


  #
  # Report Display Name
  # A human-readable name for a report of this kind, used on the site to reference these reports
  #

  # Subclass should overwrite this abstract property, which is then accessible through the getter below
  @property
  @abstractmethod
  def _report_display_name(self) -> str:
    pass

  @classmethod
  def get_report_display_name(cls):
    return cls._report_display_name


  #
  # Path values
  # Fill in some of the path variables from GCPReport using the Entity methods
  #

  @classmethod
  def _report_path_prefix(cls):
    return 'reports'

  @property
  def _report_prefix(self):
    return '/'.join([ self._report_path_prefix(), self.container_name, self.container_version, super()._report_prefix ])


  #
  # Cache
  #

  @classmethod
  def find_cached_submissions(cls, data_id: Union[str, Enum], user: User = None, container: Container = None, status: JobStatus = None) -> list:
    '''
      Retrieve all reports with the given data ID, optionally filtering by the user, container, and status.
    '''

    # If data ID is an enum, map to name (string value)
    if isinstance(data_id, Enum):
      data_id = data_id.name

    # Check for reports by this user with a matching data hash
    filters = [
      (cls._data_id_field, '=', data_id),
    ]

    # If user provided, add to filter list
    if user is not None:
      filters.append(('username', '=', user.name))

    # Convert status to iterable (set), if a single value passed
    if status is not None and not hasattr(status, '__iter__'):
      status = {status}

    # Loop through each matching report, sorted newest to oldest and prioritizing matches with a date
    # Filter based on container and/or status, based on which args are provided
    return [
      match for match in cls.sort_by_created_date( cls.query_ds(filters=filters), set_none_max=True )
        if  ( container is not None and match.container_equals(container) )
        and ( status    is not None and match['status'] in status )
    ]


  def check_cached_result(self):
    return check_blob_exists(self.get_bucket_name(), self.get_result_blob_path())
