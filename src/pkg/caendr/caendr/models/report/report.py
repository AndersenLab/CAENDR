from abc import ABC, abstractmethod
from typing import Optional

from caendr.models.status import JobStatus

from google.cloud.storage.blob     import Blob
from caendr.services.cloud.storage import BlobURISchema



class Report(ABC):
  '''
    Abstract template class representing a job report.

    Mediates storage with a datastore provider:
      - Job metadata
      - Input and output files
      - The submitting user
      - Version of the container to use when running the job
      - Status of the job pipeline

    Optionally supports checking for cached submissions and cached results.
  '''


  #
  # Identifiers
  # Taken together, these should define a unique report.
  #

  @property
  @abstractmethod
  def kind(self) -> str:
    '''
      The type of job represented by this report. Shared by all jobs of the same type, regardless of the data they represent.

      See: `data_id`, `id`.
    '''
    pass

  @classmethod
  @abstractmethod
  def get_kind(cls) -> str: pass


  @abstractmethod
  def get_data_id(self, as_str=False):
    '''
      A string identifying the data held in this report, e.g. a hash. Shared by all jobs computing this same data.

      Reports with the same data ID will be considered to represent the same "computation".

      Most likely, will not be affected by:
        - the submitting user (see `set_user`, `get_user`)
        - the runtime container (see `set_container`, `get_container`)
    '''
    pass


  @property
  @abstractmethod
  def id(self) -> str:
    '''
      A string identifying this specific report. Should be unique within its `kind`.
    '''
    pass



  #
  # Instantiation
  #

  # Direct initialization of a Report object should be prevented.
  # Instead, one of the factory methods `create` or `lookup` should be used.

  @classmethod
  @abstractmethod
  def create(**kwargs):
    '''
      Create a new report with the given properties.
      The kind is determined by the subclass used to call this method.
    '''
    pass

  @classmethod
  @abstractmethod
  def lookup(report_id: str):
    '''
      Lookup the report in the datastore with the given report ID.
      The kind is determined by the subclass used to call this method.
    '''
    pass



  #
  # Arbitrary metadata properties
  #

  @abstractmethod
  def __getitem__():
    '''
      Get the value of a metadata property on this report.
    '''
    pass

  @abstractmethod
  def __setitem__():
    '''
      Set the value of a metadata property on this report.
    '''
    pass



  #
  # User
  #

  @abstractmethod
  def set_user(self, user):
    '''
      Mark the provided user as the owner of this job.
      May involve e.g. setting any metadata fields or properties relating to the user.

      Note that the `save()` method must be used to propagate any local changes to the datastore.
    '''
    pass

  @abstractmethod
  def get_user(self):
    '''
      Get an object representing the owner of this job.
    '''
    pass

  @abstractmethod
  def belongs_to_user(self, user) -> bool:
    pass



  #
  # Container
  #

  @abstractmethod
  def set_container(self, container):
    '''
      Set the container to be used to run this job.
      May involve e.g. setting any metadata fields or properties relating to the user.

      Note that the `save()` method must be used to propagate any local changes to the datastore.
    '''
    pass

  @abstractmethod
  def get_container(self):
    '''
      Get an object representing the container to be used to run this job.
    '''
    pass



  #
  # Status
  #

  @abstractmethod
  def set_status(self, status: JobStatus):
    '''
      Record the status of this job.

      Note that the `save()` method must be used to propagate any local changes to the datastore.
    '''
    pass

  @abstractmethod
  def get_status(self) -> JobStatus:
    '''
      Get the status of this job.
    '''
    pass



  #
  # Saving data to datastore
  #

  @abstractmethod
  def save(self):
    '''
      Update the metadata in the datastore using the local fields.

      Note that, until this function is called, any changes to metadata properties should NOT be stored in the datastore.
    '''
    pass

  @abstractmethod
  def upload(self, *files):
    '''
      Upload one or more input files for this job.
      Subclasses may perform validation on the number of files.
    '''
    pass



  #
  # Directory functions
  #


  def report_directory(self, *path, schema: BlobURISchema = None):
    '''
      Get a filepath within the data directory.
    '''
    pass

  def data_directory(self, *path, schema: BlobURISchema = None):
    '''
      Get a filepath within the tool directory.
    '''
    pass

  def work_directory(self, *path, schema: BlobURISchema = None):
    '''
      Get a filepath within the work directory.
    '''
    pass

  def input_directory(self, *path, schema: BlobURISchema = None):
    '''
      Get a filepath within the input directory.
    '''
    pass

  def output_directory(self, *path, schema: BlobURISchema = None):
    '''
      Get a filepath within the output directory.
    '''
    pass



  #
  # Data paths
  # Bundles together a number of paths under common names, to be used in job execution
  # May be overwritten / added to in subclasses
  #

  def get_data_paths(self, schema: BlobURISchema):
    return {
      'WORK_DIR':   self.work_directory(schema=schema),
      'DATA_DIR':   self.data_directory(schema=schema),
      'OUTPUT_DIR': self.output_directory(schema=schema),
    }



  #
  # Retrieving data from datastore
  #


  def fetch(self):
    '''
      Fetch all data for this job from the file storage provider.
      Equivalent to calling `fetch_input` and `fetch_output` with this object.

      Arguments:
        - `raw` (`bool`): If `true`, return the raw blob(s); otherwise, parse into a Python object. Default `false`.

      Returns:
        - `input`: The input file(s)
        - `output`: The output file(s)
    '''
    return self.fetch_input(), self.fetch_output()


  @abstractmethod
  def fetch_input(self) -> Optional[Blob]:
    '''
      Fetch the input data from the datastore.
      This should retrieve any file(s) created / uploaded by the `upload` method.
    '''
    pass


  @abstractmethod
  def fetch_output(self) -> Optional[Blob]:
    '''
      Fetch the output data from the datastore.
      This should retrieve any file(s) created / uploaded by the tool execution.
    '''
    pass



  #
  # Cache
  #

  @classmethod
  @abstractmethod
  def find_cached_submissions(cls, data_id, user = None, container = None, status: JobStatus = None) -> list:
    '''
      Retrieve all reports with the given data ID, optionally filtering by the user, container, and status.
    '''
    return []
