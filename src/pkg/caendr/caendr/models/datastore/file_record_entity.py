from abc import ABC, abstractmethod

from caendr.models.datastore       import Entity
from caendr.services.cloud.storage import BlobURISchema, generate_blob_uri, check_blob_exists, get_blob, get_blob_if_exists
from caendr.utils.tokens           import TokenizedString



class FileRecordEntity(Entity, ABC):
  '''
    An entity tracking a file (or file template) in the database.

    Can be used to store a single template pattern for a set of related files,
    where the path is a tokenized (parameterized) string.
    This is useful if e.g. all species have their own unique copy of a specific file.
  '''

  #
  # Properties
  #

  @classmethod
  def get_props_set(cls):
    return {
      *super().get_props_set(),
      'filename',
    }


  #
  # Filepath
  #

  @property
  @abstractmethod
  def bucket(self) -> str:
    '''
      The name of the bucket containing this entity's file.

      By default, this is not stored as a prop in the Entity -- instead, it is meant to be computed from other props.
      If the raw prefix needs to be saved directly, it could be added as a prop in the subclass,
      along with overrides for the getter/setter methods.
    '''
    pass

  @property
  @abstractmethod
  def prefix(self) -> TokenizedString:
    '''
      The location of this entity's file within the bucket.

      By default, this is not stored as a prop in the Entity -- instead, it is meant to be computed from other props.
      If the raw prefix needs to be saved directly, it could be added as a prop in the subclass,
      along with overrides for the getter/setter methods.
    '''
    pass


  #
  # Filename property
  #

  @property
  def filename(self) -> TokenizedString:
    '''
      The name of the file itself. Returns as a `TokenizedString`.
    '''
    if self._get_raw_prop('filename') is None:
      return None
    return TokenizedString( self._get_raw_prop('filename') )

  @filename.setter
  def filename(self, v):
    '''
      Save the name of the file itself. Saves internally as a raw string.
    '''
    if isinstance(v, TokenizedString):
      v = v.raw_string
    if not (isinstance(v, str) or v is None):
      raise ValueError(f'Cannot set prop "filename" to "{v}" (type {type(v)}): must be a string')
    return self._set_raw_prop('filename', v)


  #
  # Constructing filepath
  #

  def get_filepath(self, schema: BlobURISchema = None, check_if_exists: bool = False, **kwargs) -> str:
    '''
      Construct the full path for the file, using the provided keyword arguments to fill out the template.
    '''
    if check_if_exists and not self.check_exists(**kwargs):
      return None
    return generate_blob_uri( self.bucket, self.prefix.get_string(**kwargs), self['filename'].get_string(**kwargs), schema=schema )


  def get_filepath_template(self, schema: BlobURISchema = None) -> TokenizedString:
    '''
      Construct the full path for the file as a templated string, leaving the tokens un-filled.
    '''
    return TokenizedString.apply( generate_blob_uri, self.bucket, self.prefix, self['filename'], schema=schema )


  def get_blob(self, check_if_exists = False, **kwargs):
    '''
      Download the file as a blob, using the provided keyword arguments to fill out the filepath template.
    '''
    f = get_blob_if_exists if check_if_exists else get_blob
    return f( self.bucket, self.prefix.get_string(**kwargs), self['filename'].get_string(**kwargs) )


  #
  # Utils
  #

  def check_exists(self, **tokens):
    '''
      Check whether the file specified by the given tokens exists in the database.
      Uses the provided keyword arguments to fill out the filepath template, then checks for that filename.
    '''
    return check_blob_exists( self.bucket, self.prefix.get_string(**tokens), self['filename'].get_string(**tokens) )
  
  def check_exists_for_species(self, species, **tokens):
    return check_blob_exists(
      self.bucket,
      self.prefix.get_string( **{**TokenizedString.get_species_tokens(species), **tokens} ),
      self['filename'].get_string( **{**TokenizedString.get_species_tokens(species), **tokens} )
    )
