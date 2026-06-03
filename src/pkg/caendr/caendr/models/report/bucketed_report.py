# Built-ins
from abc import abstractmethod

# Parent class
from .report import Report

# Services
from caendr.services.cloud.storage import BlobURISchema



class BucketedReport(Report):
  '''
    Abstract class for a report storing data in a datastore that uses buckets & paths.

    Adds abstract propetryesmethods

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
  # Generate URIs
  #

  @classmethod
  @abstractmethod
  def _generate_uri(cls, bucket: str, *path: str, schema: BlobURISchema=None):
    pass

  @classmethod
  @abstractmethod
  def _list_files(cls, bucket: str, *prefix: str, filter=None):
    pass



  #
  # Bucket names
  # These are used to locate the bucket for each directory.
  # These must all be overwritten in subclasses
  #

  @property
  @abstractmethod
  def _report_bucket(self) -> str:
    '''
      Bucket where any data specific to report is stored.
    '''
    pass

  @property
  @abstractmethod
  def _data_bucket(self) -> str:
    '''
      Bucket where any data specific to tool but NOT to individual report is stored.
    '''
    pass

  @property
  @abstractmethod
  def _work_bucket(self) -> str:
    '''
      Bucket to use as temp storage for work.
    '''
    pass



  #
  # Path prefixes
  # These are each used to locate the directory for this report within each bucket
  # These may all be overwritten in subclasses
  #

  @property
  def _report_prefix(self):
    '''
      The location of this report's input/output data within the data bucket.
      By default, uses the data ID as a subfolder.
    '''
    return self.get_data_id(as_str=True)

  @property
  def _data_prefix(self):
    '''
      The location of this report's tool data within the tool bucket.
      May still depend on the individual report, e.g. if different folders exist for species or for container versions.
    '''
    return ''

  @property
  def _work_prefix(self):
    '''
      The location of this report's work within the work bucket.
      By default, uses the data ID as a subfolder.
    '''
    return self.get_data_id(as_str=True)

  @property
  def _input_prefix(self):
    '''
      The location of the report's input data within the data directory.
    '''
    return ''

  @property
  def _output_prefix(self):
    '''
      The location of the report's output data within the data directory.
    '''
    return ''



  #
  # Directory functions
  # These probably should not be overwritten, unless you're sure you know what you're doing.
  # Instead, look into overwriting the bucket functions, prefix functions, and _generate_uri
  # to customize directory lookups.
  #

  def report_directory(self, *path, schema: BlobURISchema = None):
    return self._generate_uri( self._report_bucket, self._report_prefix, *path, schema=schema )

  def data_directory(self, *path, schema: BlobURISchema = None):
    return self._generate_uri( self._data_bucket, self._data_prefix, *path, schema=schema )

  def work_directory(self, *path, schema: BlobURISchema = None):
    return self._generate_uri( self._work_bucket, self._work_prefix, *path, schema=schema )

  def input_directory(self, *path, schema: BlobURISchema = None):
    return self.report_directory( self._input_prefix,  *path,  schema=schema )

  def output_directory(self, *path, schema: BlobURISchema = None):
    return self.report_directory( self._output_prefix, *path, schema=schema )



  #
  # Directory listing functions
  # Each returns the list of blobs in the given directory, with an optional extra path & filter.
  #
  # These probably should not be overwritten, unless you're sure you know what you're doing.
  # Instead, look into overwriting the bucket functions, prefix functions, and _list_files
  # to customize directory lookups.
  #

  def _list_directory(self, f_dir, *path, filter=None):
    return self._list_files( *f_dir(*path, schema=BlobURISchema.PATH), filter=filter )

  def list_report_directory(self, *path, filter=None):
    return self._list_directory( self.report_directory, *path, filter=filter )

  def list_data_directory(self, *path, filter=None):
    return self._list_directory( self.data_directory,   *path, filter=filter )

  def list_work_directory(self, *path, filter=None):
    return self._list_directory( self.work_directory,   *path, filter=filter )

  def list_input_directory(self, *path, filter=None):
    return self._list_directory( self.input_directory,  *path, filter=filter )

  def list_output_directory(self, *path, filter=None):
    return self._list_directory( self.output_directory, *path, filter=filter )
