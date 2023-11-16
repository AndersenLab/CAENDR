import os

from caendr.services.cloud.storage import BlobURISchema, generate_blob_uri, download_blob_to_file, join_path
from caendr.utils.tokens           import TokenizedString
from caendr.utils.file             import unzip_gz, get_zipped_file_ext



LOCAL_DIR = os.path.join('.', '.download')
os.makedirs(LOCAL_DIR, exist_ok=True)



class LocalDatastoreFile(os.PathLike):
  '''
    Manage a local copy of a file in the datastore.
  '''

  # Default location to store files locally
  _DEFAULT_LOCAL_PATH = LOCAL_DIR


  #
  # Instantiation
  #

  def __init__(self, file_id: str, bucket: str, *path: str, unzip: bool = False, local_path: str = None):

    # Validate path length
    if not len(path):
      raise ValueError('Must provide at least one path element')

    # Save vars locally
    self._file_id = file_id
    self._bucket  = bucket
    self._path    = path
    self._unzip   = unzip

    # Get the file extension as the last section of the path after a '.', ignoring '.gz'
    # If there is no file extension (e.g. 'foobar.gz' or just 'foobar'), set to empty string
    self._file_ext = get_zipped_file_ext( path[-1] )[0] or ''

    # Set the local path
    self._LOCAL_PATH = local_path if local_path is not None else self._DEFAULT_LOCAL_PATH


  #
  # Datastore file
  #

  def get_datastore_uri(self, schema: BlobURISchema = None):
    '''
      Get a path to the file in the datastore.
    '''
    return generate_blob_uri(self._bucket, *self._path, schema=schema)

  @property
  def source_is_zipped(self):
    return self._path[-1][-3:] == '.gz'


  #
  # Local file
  #

  def get_local_filename(self, zipped: bool = True):
    '''
      Get a local name for the file once it's been downloaded. No filepath.
    '''
    return self._file_id + self._file_ext + ('.gz' if zipped else '')

  def get_local_filepath(self, zipped: bool = True):
    '''
      Get a local path to the file once it's been downloaded. Full path.
    '''
    return join_path(self._LOCAL_PATH, self.get_local_filename(zipped=zipped))

  def exists_local(self, zipped: bool = True):
    '''
      Check whether the file exists locally (i.e. is cached).
    '''
    return os.path.exists( self.get_local_filepath(zipped=zipped) )
  
  def __fspath__(self):
    return self.get_local_filepath(zipped = not self._unzip)


  #
  # Fetch
  #

  def fetch( self, use_cache: bool = True ):

    # Check if file is already downloaded and unzipped
    if use_cache and self.exists_local(zipped=False):
      local_is_zipped = False

    # Check if file is already downloaded and zipped
    elif use_cache and self.exists_local(zipped=True):
      local_is_zipped = True

    # Download the external file
    else:
      download_blob_to_file(self._bucket, *self._path, destination=self._LOCAL_PATH, filename=self.get_local_filename(zipped = self.source_is_zipped))
      local_is_zipped = self.source_is_zipped

    # Unzip the downloaded file, if applicable
    if local_is_zipped and self._unzip:
      unzip_gz(self.get_local_filepath(zipped = True), keep_zipped_file=False)

    # Return the resulting filename
    return self.get_local_filepath(zipped = not self._unzip)




class LocalDatastoreFileTemplate():
  '''
    Manage a template for building LocalDatabaseFile objects, parameterized by species & other tokens.
  '''

  # Default directory to store files locally
  _DEFAULT_LOCAL_PATH = TokenizedString(os.path.join(LOCAL_DIR, '${SPECIES}'))

  def __init__(self, file_id: str, bucket: str, *path: TokenizedString):
    self._file_id = file_id
    self._bucket  = bucket
    self._path    = path


  def _build_path(self, species=None, tokens={}):
    return [
      ts.get_string( **{**TokenizedString.get_species_tokens(species), **tokens} ) for ts in self._path
    ]


  def build(self, species=None, tokens={}):
    '''
      Build a `LocalDatastoreFile` object using this object's template and the provided species & tokens.
    '''
    return LocalDatastoreFile(
      self._file_id,
      self._bucket,
      *self._build_path(species=species, tokens=tokens),
      unzip = False,
      local_path = self._DEFAULT_LOCAL_PATH.get_string( **{**TokenizedString.get_species_tokens(species), **tokens} )
    )
