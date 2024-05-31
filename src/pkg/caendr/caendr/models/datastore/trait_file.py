from typing import Tuple, Optional
from enum import Enum

from caendr.utils.env import get_env_var

from caendr.models.datastore       import FileRecordEntity, PublishableEntity, SpeciesEntity, UserOwnedEntity
from caendr.services.cloud.storage import BlobURISchema, join_path
from caendr.utils.tokens           import TokenizedString


DB_BUCKET_NAME = get_env_var('MODULE_DB_OPERATIONS_BUCKET_NAME')


class DatasetType(Enum):
  """ Identifier for trait files folder in GCP Buckets """
  CAENDR  = 'caendr'
  PUBLIC  = 'public'
  ZHANG   = 'zhang'

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
      'trait_name_caendr',
      'dataset',

      # About trait (display info)
      'trait_name_user',
      'trait_name_display_1',
      'trait_name_display_2',
      'trait_name_display_3',
      'description_short',
      'description_long',
      'units',
      'tags',

      # Source information
      'publication',
      'protocols',
      'source_lab',
      'institution',
      'capture_date',

      # Other
      'is_bulk_file',
    }


  def serialize(self, include_meta=True):
    return {
      **super().serialize(include_meta=include_meta),

      # Add Python property values & function lookups
      'name':            self.name,
      'uri':             self.get_filepath(schema=BlobURISchema.HTTPS),
      'submitter':       self.get_user_full_name() if self.from_public else 'CaeNDR',
      'submitter_email': self.get_user_email() if self.from_public else None,
      'is_public':       self.is_public,
      'from_caendr':     self.from_caendr,
    }


  #
  # Path
  #

  @property
  def bucket(self):
    return DB_BUCKET_NAME

  @property
  def prefix(self):
    if self.dataset == DatasetType.PUBLIC:
      return TokenizedString(join_path('trait_files', self['dataset'].value, '${SPECIES}', '${USER_ID}'))
    return TokenizedString(join_path('trait_files', self['dataset'].value, '${SPECIES}'))


  #
  # Filename
  #

  # The species is always determined by this entity itself, so we fill it in instead of letting the calling function supply it
  def get_filepath(self, schema: BlobURISchema = None, check_if_exists: bool = False):
    if self.dataset == DatasetType.PUBLIC:
      return super().get_filepath_hashed(schema=schema, check_if_exists=check_if_exists, SPECIES=self['species'].name, USER_ID=self['username'])
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


  @property
  def display_name(self) -> Tuple[str, Optional[str], Optional[str]]:
    '''
      The trait display name as a tuple.  The first element will always exist.

      Combines `trait_name_display_1`, `trait_name_display_2`, and `trait_name_display_3` into a single tuple.
    '''
    return self['trait_name_display_1'], self['trait_name_display_2'] or '', self['trait_name_display_3'] or ''

  @property
  def dataset(self):
    return self._get_enum_prop(DatasetType, 'dataset', None)
  
  @dataset.setter
  def dataset(self, val):
    if isinstance(val, str):
      val = val.upper()
    return self._set_enum_prop(DatasetType, 'dataset', val)