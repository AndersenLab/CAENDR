# Built-ins
from abc import abstractmethod

# Parent class
from .bucketed_report import BucketedReport

# Services
from caendr.services.cloud.storage import upload_blob_from_string, upload_blob_from_file, BlobURISchema, generate_blob_uri
from caendr.utils.env              import get_env_var



MODULE_SITE_BUCKET_PRIVATE_NAME = get_env_var('MODULE_SITE_BUCKET_PRIVATE_NAME')
MODULE_SITE_BUCKET_PUBLIC_NAME  = get_env_var('MODULE_SITE_BUCKET_PUBLIC_NAME')

MODULE_API_DATA_BUCKET_NAME     = get_env_var('MODULE_API_PIPELINE_TASK_DATA_BUCKET_NAME')



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
  # By default, all use the private GCP bucket.
  #

  @property
  def _report_bucket(self) -> str:
    '''
      Bucket where any data specific to report is stored.
    '''
    return MODULE_SITE_BUCKET_PRIVATE_NAME

  @property
  def _data_bucket(self) -> str:
    '''
      Bucket where any data specific to tool but NOT to individual report is stored.
    '''
    return MODULE_SITE_BUCKET_PRIVATE_NAME

  @property
  def _work_bucket(self) -> str:
    '''
      Bucket to use as temp storage for work.
    '''
    return MODULE_SITE_BUCKET_PRIVATE_NAME


  #
  # Input/Output
  #

  @property
  @abstractmethod
  def _input_filename(self):
    pass

  @property
  @abstractmethod
  def _output_filename(self):
    pass


  def input_filepath(self, schema: BlobURISchema = None):
    return self.input_directory(  self._input_filename,  schema=schema )

  def output_filepath(self, schema: BlobURISchema = None):
    return self.output_directory( self._output_filename, schema=schema )



  #
  # Saving data to datastore
  # Implementing method(s) in parent class
  #

  def upload(self, *data_files):

    # Get the location of the input directory
    bucket, path = self.input_filepath(schema = BlobURISchema.PATH)

    # Upload based on argument type
    for df in data_files:
      if isinstance(df, str):
        upload_blob_from_string(bucket, df, path)
      else:
        upload_blob_from_file(bucket, df, path)
