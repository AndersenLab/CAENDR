import os
import pathlib

from caendr.services.logger        import logger

from .foreign_resource             import ForeignResource, ForeignResourceTemplate

from caendr.models.datastore       import Species, FileRecordEntity
from caendr.models.error           import NotFoundError, ForeignResourceMissingError, ForeignResourceUndefinedError
from caendr.services.cloud.storage import BlobURISchema, generate_blob_uri, download_blob_to_file, join_path, check_blob_exists
from caendr.utils.tokens           import TokenizedString
from caendr.utils.file             import get_zipped_file_ext



LOCAL_DIR = pathlib.Path('.', '.download')
os.makedirs(LOCAL_DIR, exist_ok=True)



class LocalDatastoreFile(os.PathLike, ForeignResource):
  '''
    Manage a local copy of a file in the datastore.
  '''

  # Default location to store files locally
  _DEFAULT_LOCAL_PATH = LOCAL_DIR


  #
  # Instantiation
  #

  def __init__(self, resource_id: str, bucket: str, *path: str, local_path: str = None, metadata: dict = None):

    # Validate path length
    if not len(path):
      raise ValueError('Must provide at least one path element')

    # Save resource ID
    super().__init__(resource_id)

    # Save vars locally
    self._bucket   = bucket
    self._path     = path
    self._metadata = metadata or {}

    # Get the file extension as the last section of the path after a '.', ignoring '.gz'
    # If there is no file extension (e.g. 'foobar.gz' or just 'foobar'), set to empty string
    self._file_ext, self._is_zipped = get_zipped_file_ext( path[-1] )
    if self._file_ext is None:
      self._file_ext = ''

    # Set the local path
    self._local_path = pathlib.Path(local_path) if local_path is not None else self._DEFAULT_LOCAL_PATH


  #
  # Printing
  #

  def __repr__(self):
    return f'Datastore file "{self.resource_id}": ' + join_path( *self.get_datastore_uri(schema=BlobURISchema.PATH) )

  def __print_locations(self):
    return f'{self.get_local_filepath()}  <-  {self.get_datastore_uri(schema=BlobURISchema.HTTPS)}'


  #
  # File extension
  #

  @property
  def is_zipped(self):
    return self._is_zipped

  @property
  def file_ext(self):
    return self._file_ext

  @property
  def file_ext_full(self):
    return self.file_ext + ('.gz' if self.is_zipped else '')


  #
  # Datastore file
  #

  def get_datastore_uri(self, schema: BlobURISchema = None):
    '''
      Get a path to the file in the datastore.
    '''
    return generate_blob_uri(self._bucket, *self._path, schema=schema)

  def exists_in_ds(self):
    return check_blob_exists(self._bucket, *self._path)


  #
  # Local file
  #

  def get_local_filename(self):
    '''
      Get a local name for the file once it's been downloaded. No filepath.
    '''
    return self.resource_id + self.file_ext_full

  def get_local_filepath(self):
    '''
      Get a local path to the file once it's been downloaded. Full path.
    '''
    return os.path.join(self._local_path, self.get_local_filename())

  def exists_local(self):
    '''
      Check whether the file exists locally (i.e. is cached).
    '''
    return os.path.exists( self.get_local_filepath() )


  #
  # PathLike
  #

  def __fspath__(self):
    return self.get_local_filepath()


  #
  # ForeignResource
  #

  @property
  def metadata(self):
    return self._metadata or {}


  def fetch_resource( self, use_cache: bool = True ):
    '''
      Ensure the file exists locally in the desired format, and return the local filepath.
    '''

    # Check if file has already been downloaded
    if use_cache and self.exists_local():
      logger.info(f'Already downloaded datastore file [{self.resource_id}]:\n\t{ self.__print_locations() }')

    # Try downloading the file
    else:
      try:
        logger.info(f'Downloading datastore file [{self.resource_id}]:\n\t{ self.__print_locations() }')
        download_blob_to_file(self._bucket, *self._path, destination=self._local_path, filename=self.get_local_filename())
        logger.info(f'Completed download of file [{self.resource_id}]:\n\t{ self.__print_locations() }')

      # If not found, wrap error
      except NotFoundError as ex:
        raise ForeignResourceMissingError(self) from ex

    # # Unzip the downloaded file, if applicable
    # # NOTE: Deprecated -- none of our resources use this, so it just introduces potential vulnerabilities later
    # if local_is_zipped and self._unzip:
    #   logger.info(f'Unzipping {self.get_local_filepath(zipped = True)} ...')
    #   unzip_gz(self.get_local_filepath(zipped = True), keep_zipped_file=False)

    # Return the local filepath
    return self.__fspath__()



class LocalDatastoreFileTemplate(ForeignResourceTemplate):
  '''
    Manage a template for building LocalDatabaseFile objects, parameterized by species & other tokens.

    Implements `SpeciesDict`. Returns `LocalDatastoreFile` object for a given species.
  '''

  # Default directory to store files locally
  _DEFAULT_LOCAL_PATH = TokenizedString(os.path.join(LOCAL_DIR, '${SPECIES}'))

  def __init__(self, resource_id: str, bucket: str, *path: TokenizedString, exists_for_species=None, metadata=None):
    super().__init__(resource_id)
    self._bucket = bucket
    self._path   = path

    self.__exists_for_species = exists_for_species
    self.__metadata = metadata or {}


  @staticmethod
  def from_file_record_entity(record: FileRecordEntity):
    '''
      Factory method to instantiate a template from a `FileRecordEntity` object.
      Uses the file as the foreign resource, and the `Entity` as the metadata.
    '''
    # Check if the entity tracks a species field
    try:
      species = {record['species']}
    except KeyError:
      species = None

    # Create the template object
    return LocalDatastoreFileTemplate( record.name, *record.get_filepath(schema=BlobURISchema.PATH), exists_for_species=species, metadata=record )


  @staticmethod
  def from_file_record_entities(entity_class, filter = None):
    '''
      Factory method to instantiate multiple templates from all Datastore entities of the given class.

      Arguments:
        - `entity_class`: The `FileRecordEntity` subclass to query and use to instantiate the templates.
        - `filter`:
            An optional filtering function.
            If provided, only creates templates from entities that pass the filter;
            if omitted, creates a template from all entities of the appropriate kind.
    '''
    if filter is None:
      filter = lambda x: True
    return [
      LocalDatastoreFileTemplate.from_file_record_entity(record) for record in entity_class.query_ds() if filter(record)
    ]



  #
  # Building
  #

  def _build_path(self, species=None, tokens={}):
    return [
      ts if isinstance(ts, str) else ts.get_string( **{**TokenizedString.get_species_tokens(species), **tokens} ) for ts in self._path
    ]


  def build(self, species=None, tokens={}):
    '''
      Build a `LocalDatastoreFile` object using this object's template and the provided species & tokens.
    '''
    return LocalDatastoreFile(
      self.resource_id,
      self._bucket,
      *self._build_path(species=species, tokens=tokens),
      local_path = self._DEFAULT_LOCAL_PATH.get_string( **{**TokenizedString.get_species_tokens(species), **tokens} ),
      metadata   = self.__metadata,
    )


  #
  # ForeignResourceTemplate
  #

  def get_print_uri(self, species: Species) -> str:
    return join_path( *self.build(species).get_datastore_uri(schema=BlobURISchema.PATH) )

  def check_exists(self, species: Species) -> bool:
    return self.build(species).exists_in_ds()

  def has_for_species(self, species: Species):
    return self.__exists_for_species is None or species in self.__exists_for_species

  def get_for_species(self, species: Species):

    # Check that species is valid
    if not self.has_for_species(species):
      raise ForeignResourceUndefinedError('Datastore file', self.resource_id, species)

    # Build the template using the given species
    return self.build(species)
