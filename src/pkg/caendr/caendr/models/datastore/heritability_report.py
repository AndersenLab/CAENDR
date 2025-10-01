from caendr.models.datastore import HashableEntity, ReportEntity

from caendr.services.cloud.storage import BlobURISchema
from caendr.utils.env              import get_env_var


PRIVATE_BUCKET_NAME = get_env_var('MODULE_SITE_BUCKET_PRIVATE_NAME')


class HeritabilityReport(HashableEntity, ReportEntity):

  #
  # Class Variables
  #

  kind = 'heritability_report'

  _report_display_name = 'Heritability'

  # Identify the report data by the data hash, inherited from the HashableEntity parent class
  _data_id_field = 'data_hash'


  #
  # Path
  #

  # TODO: Move data files to Data bucket
  @property
  def _data_bucket(self) -> str:
    return PRIVATE_BUCKET_NAME

  # TODO: Standardize data prefix for all tools
  @property
  def _data_prefix(self):
    return 'tool_release_data'

  def get_data_paths(self, schema: BlobURISchema):
    return {
      **super().get_data_paths(schema=schema),
      'TRAIT_FILE': self.input_filepath(schema=schema),
    }


  #
  # Input & Output
  #

  _num_input_files = 1
  _input_filename  = 'data.tsv'
  _output_filename = 'heritability_result.tsv'


  #
  # Properties
  #

  @classmethod
  def get_props_set(cls):
    return {
      *super().get_props_set(),
      'species',
      'label',
      'trait',
    }
