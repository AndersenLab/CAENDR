from caendr.utils.env import get_env_var

from caendr.models.datastore       import FileRecordEntity, PublishableEntity, SpeciesEntity, UserOwnedEntity
from caendr.services.cloud.storage import BlobURISchema
from caendr.utils.tokens           import TokenizedString


DB_BUCKET_NAME = get_env_var('MODULE_DB_OPERATIONS_BUCKET_NAME')



class TraitFile(FileRecordEntity, PublishableEntity, SpeciesEntity, UserOwnedEntity):

  kind = 'trait_file'


  #
  # Properties
  #

  @classmethod
  def get_props_set(cls):
    return {
      *super().get_props_set(),

      # Identifying trait
      'trait_name',
      'species',
      'is_bulk_file',

      # About trait
      'description_short',
      'description_long',
      'units',

      # Source information
      'doi',
      'protocols',
      'source_lab',
    }


  #
  # Path
  #

  @property
  def bucket(self):
    return DB_BUCKET_NAME

  @property
  def prefix(self):

    # If published by CaeNDR, go to CaeNDR folder
    if self.from_caendr:
      return TokenizedString('trait_files/caendr/{SPECIES}')

    # If public user submission, go to user folder
    return TokenizedString('trait_files/public/{SPECIES}')


  #
  # Filename
  #

  # The species is always determined by this entity itself, so we fill it in instead of letting the calling function supply it
  def get_filepath(self, schema: BlobURISchema = None, check_if_exists: bool = False):
    return super().get_filepath(schema=schema, check_if_exists=check_if_exists, SPECIES=self['species'].name)


  #
  # Source properties
  #

  @property
  def is_bulk_file(self):
    return self._get_raw_prop('is_bulk_file', False)
  
  @is_bulk_file.setter
  def is_bulk_file(self, val):
    return self._set_raw_prop('is_bulk_file', bool(val))
