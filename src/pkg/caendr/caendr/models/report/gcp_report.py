# Built-ins
from abc import abstractmethod

# Parent class
from .bucketed_report import BucketedReport

# Services
from caendr.services.cloud.storage import check_blob_exists, get_blob_if_exists, get_blob_list, upload_blob_from_string, upload_blob_from_file, BlobURISchema, generate_blob_uri
from caendr.utils.env              import get_env_var
from caendr.utils.local_file       import LocalFile


# Bucket names
PRIVATE_BUCKET_NAME = get_env_var('MODULE_SITE_BUCKET_PRIVATE_NAME')
DATA_BUCKET_NAME    = get_env_var('MODULE_API_PIPELINE_TASK_DATA_BUCKET_NAME')
WORK_BUCKET_NAME    = get_env_var("MODULE_API_PIPELINE_TASK_WORK_BUCKET_NAME")



class GCPReport(BucketedReport):
  '''
    Abstract class for a report storing data in GCP.

    Implements the upload method

    Partially implements fetch methods -- gets raw blobs.  Subclasses should use super() and fully implement these.

    Default file structure:
        - `{ report bucket }/{ report prefix }`
            - `{ input prefix }/` ...
            - `{ output prefix }/` ...
        - `{ data bucket }/{ data prefix }/` ...
        - `{ work bucket }/{ work prefix }/` ...

    Note that, by default, the `input` and `output` directories are assumed to live within the `report` directory.
    This behavior may be overwritten by subclasses.
  '''


  #
  # Generating URIs
  #

  @classmethod
  def _generate_uri(cls, bucket: str, *path: str, schema: BlobURISchema=None):
    return generate_blob_uri(bucket, *path, schema=schema)


  #
  # Bucket names
  #

  @property
  def _report_bucket(self) -> str:
    return PRIVATE_BUCKET_NAME

  @property
  def _data_bucket(self) -> str:
    return DATA_BUCKET_NAME

  @property
  def _work_bucket(self) -> str:
    return WORK_BUCKET_NAME


  #
  # Input & output paths
  #

  @property
  @abstractmethod
  def _input_filename(self):
    pass

  @property
  @abstractmethod
  def _output_filename(self):
    pass


  def input_filepath(self, schema: BlobURISchema = None, check_if_exists: bool = False):
    if check_if_exists and not check_blob_exists(*self.input_directory( self._input_filename, schema=BlobURISchema.PATH )):
      return None
    return self.input_directory(  self._input_filename,  schema=schema )

  def output_filepath(self, schema: BlobURISchema = None, check_if_exists: bool = False):
    if check_if_exists and not check_blob_exists(*self.output_directory( self._output_filename, schema=BlobURISchema.PATH )):
      return None
    return self.output_directory( self._output_filename, schema=schema )



  #
  # Saving data to datastore
  # Implementing method(s) in parent class
  #

  # The expected number of data files
  # May be overwritten in subclass to add a length check
  _num_input_files = None

  # Implement parent method
  def upload(self, *data_files):

    # If this report type expects a specific number of input files, check how many were provided
    if self._num_input_files is not None and len(data_files) != self._num_input_files:
      raise ValueError(f'Expected {self._num_input_files} data file(s) to upload for job of type {self.kind}, got {len(data_files)} file(s) instead.')

    if not len(data_files):
      return

    # Get the location of the input directory
    bucket, path = self.input_filepath(schema = BlobURISchema.PATH)

    # Upload based on argument type
    for df in data_files:
      if isinstance(df, str):
        upload_blob_from_string(bucket, df, path)
      elif isinstance(df, LocalFile):
        upload_blob_from_file(bucket, df.local_path, path)
      else:
        upload_blob_from_file(bucket, df, path)



  #
  # Retrieving data from datastore
  # Implements abstract method(s) from parent class
  #

  def fetch_input(self):
    return get_blob_if_exists( *self.input_filepath(schema=BlobURISchema.PATH) )

  def fetch_output(self):
    return get_blob_if_exists( *self.output_filepath(schema=BlobURISchema.PATH) )

  def list_output_blobs(self):
    return get_blob_list( *self.output_directory(schema=BlobURISchema.PATH) )



  #
  # Checking for files in datastore
  # Implements abstract method(s) from parent class
  #

  def check_input_exists(self) -> bool:
    return check_blob_exists( *self.input_filepath(schema=BlobURISchema.PATH) )

  def check_output_exists(self) -> bool:
    return check_blob_exists( *self.output_filepath(schema=BlobURISchema.PATH) )
