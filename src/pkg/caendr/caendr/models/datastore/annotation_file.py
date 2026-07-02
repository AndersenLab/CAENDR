from collections import OrderedDict

from caendr.utils.env import get_env_var

from caendr.models.datastore           import FileRecordEntity, SpeciesEntity
from caendr.services.cloud.aws_storage import AWSBlobURISchema, join_path
from caendr.utils.tokens               import TokenizedString
from caendr.services.logger import logger


AWS_OPEN_DATA_BUCKET = get_env_var('AWS_OPEN_DATA_BUCKET')


class AnnotationFile(FileRecordEntity, SpeciesEntity):

  kind = 'annotation'

  #
  # Properties
  #

  @classmethod
  def get_props_set(cls):
    return {
      *super().get_props_set(),

        'name',                # Name of annotation tool
        'display_name',
    }

  @staticmethod
  def release_prefix():
    '''
      Get the default prefix for the browser track files, within a dataset release folder.
    '''
    return DatasetRelease.get_path_template() + '/variation'


  def serialize(self, **kwargs):
    props = {
      **super().serialize(**kwargs),

      # Add Python property values & function lookups
      'uri':             self.get_filepath(schema=AWSBlobURISchema.HTTPS),
    }
    return props


  #
  # Path
  #

  @property
  def bucket(self):
    return AWS_OPEN_DATA_BUCKET

  @property
  def prefix(self):
    return TokenizedString(join_path('dataset_release', '${SPECIES}', '${RELEASE}', 'variation'))

  # The species is always determined by this entity itself, so we fill it in instead of letting the calling function supply it
  def get_filepath(self, schema: AWSBlobURISchema = None, check_if_exists: bool = False):
    return super().get_filepath(schema=schema, check_if_exists=check_if_exists, SPECIES=self['species'].name, RELEASE=self['species'].release_sva)

  @staticmethod
  def all():
      return ANNOTATION_LIST

# Load annotation list
ANNOTATION_LIST = {
    e.name: e for e in AnnotationFile.query_ds()
}
ANNOTATION_LIST: 'OrderedDict[str, Annotation]' = OrderedDict(sorted(ANNOTATION_LIST.items(), key=lambda e: e[1]['name']))