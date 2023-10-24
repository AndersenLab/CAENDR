# Built-ins
from abc import abstractmethod

# Parent class
from .report import Report

# Services
from caendr.services.cloud.storage import upload_blob_from_string, upload_blob_from_file, BlobURISchema, generate_blob_uri
from caendr.utils.env              import get_env_var



MODULE_SITE_BUCKET_PRIVATE_NAME = get_env_var('MODULE_SITE_BUCKET_PRIVATE_NAME')
MODULE_SITE_BUCKET_PUBLIC_NAME  = get_env_var('MODULE_SITE_BUCKET_PUBLIC_NAME')

MODULE_API_DATA_BUCKET_NAME     = get_env_var('MODULE_API_PIPELINE_TASK_DATA_BUCKET_NAME')



class GCPReport(Report):
  '''
    Abstract class for a report storing data in GCP.

    Implements the upload method
    
    Partially implements fetch methods -- gets raw blobs.  Subclasses should use super() and fully implement these.

    File structure:
        - `{ report bucket }/{ report prefix }`
            - `{ input prefix }/` ...
            - `{ output prefix }/` ...
        - `{ data bucket }/{ data prefix }/` ...
        - `{ work bucket }/{ work prefix }/` ...
  '''


  #
  # Buckets
  # These may be overwritten in subclasses
  #

  @property
  def report_bucket_name(self) -> str:
    '''
      Bucket where any data specific to report is stored.
    '''
    return MODULE_SITE_BUCKET_PRIVATE_NAME

  @property
  def data_bucket_name(self) -> str:
    '''
      Bucket where any data specific to tool but NOT to individual report is stored.
    '''
    return MODULE_SITE_BUCKET_PRIVATE_NAME

  @property
  def work_bucket_name(self) -> str:
    '''
      Bucket to use as temp storage for work.
    '''
    return MODULE_SITE_BUCKET_PRIVATE_NAME



  #
  # Path prefixes
  # These are each used to locate the directory for this report within each bucket
  # These may all be overwritten in subclasses
  #

  def _report_prefix(self):
    '''
      The location of this report's input/output data within the data bucket.
    '''
    return self.get_data_id()
    # return ''

  def _data_prefix(self):
    '''
      The location of this report's tool data within the tool bucket.
      May still depend on the individual report, e.g. if different folders exist for species or for container versions.
    '''
    return ''

  def _work_prefix(self):
    '''
      The location of this report's work within the work bucket.
    '''
    return self.get_data_id()
    # return ''

  def _input_prefix(self):
    '''
      The location of the report's input data within the data directory.
    '''
    return ''

  def _output_prefix(self):
    '''
      The location of the report's output data within the data directory.
    '''
    return ''
  


  #
  # Directory functions
  # These probably should not be overwritten, unless you're sure you know what you're doing.
  # Instead, look into overwriting the bucket, prefix, etc. functions to customize directory lookups.
  #


  def report_directory(self, *path, schema: BlobURISchema = None):
    '''
      Get a filepath within the data directory.
    '''
    return generate_blob_uri( self.report_bucket_name, self._report_prefix(), *path, schema=schema )
  
  def data_directory(self, *path, schema: BlobURISchema = None):
    '''
      Get a filepath within the tool directory.
    '''
    return generate_blob_uri( self.data_bucket_name, self._data_prefix(), *path, schema=schema )

  def work_directory(self, *path, schema: BlobURISchema = None):
    '''
      Get a filepath within the work directory.
    '''
    return generate_blob_uri( self.work_bucket_name, self._work_prefix(), *path, schema=schema )
  
  def input_directory(self, *path, schema: BlobURISchema = None):
    '''
      Get a filepath within the input directory.
    '''
    return self.report_directory( self._input_prefix(),  *path,  schema=schema )

  def output_directory(self, *path, schema: BlobURISchema = None):
    '''
      Get a filepath within the output directory
    '''
    return self.report_directory( self._output_prefix(), *path, schema=schema )




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
    return self.input_directory(  self._input_filename(),  schema=schema )

  def output_filepath(self, schema: BlobURISchema = None):
    return self.output_directory( self._output_filename(), schema=schema )

  

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
