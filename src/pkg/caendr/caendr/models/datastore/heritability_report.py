from caendr.models.datastore import HashableEntity, ReportEntity

from caendr.services.cloud.storage import BlobURISchema, generate_blob_uri
from caendr.utils.env import get_env_var



# TODO: Should this bucket be the data path?
#       Should Nemascan point here too, or should this point to the Private bucket like Nemascan?
DATA_BUCKET_NAME = get_env_var("MODULE_API_PIPELINE_TASK_DATA_BUCKET_NAME")


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

  @property
  def _data_bucket(self) -> str:
    return DATA_BUCKET_NAME

  @property
  def _data_prefix(self):
    return 'heritability'

  def get_data_paths(self, schema: BlobURISchema):
    return {
      **super().get_data_paths(schema=schema),
      'TRAIT_FILE': self.input_filepath(schema=schema),
    }


  #
  # Input & Output
  #

  _input_filename  = 'data.tsv'
  _output_filename = 'heritability_result.tsv'

  def upload(self, *data_files):
    if len(data_files) != 1:
      raise ValueError(f'Exactly one data file should be uploaded for job of type {self.kind}')
    return super().upload(*data_files)


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
