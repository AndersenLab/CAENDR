from caendr.models.datastore import DataJobEntity
from caendr.services.cloud.storage import BlobURISchema, generate_blob_uri
from caendr.utils.env import get_env_var


H2_REPORT_PATH_PREFIX = 'reports'
H2_INPUT_FILE = 'data.tsv'
H2_RESULT_FILE = 'heritability_result.tsv'

# TODO: Should this bucket be the data path?
#       Should Nemascan point here too, or should this point to the Private bucket like Nemascan?
DATA_BUCKET_NAME = get_env_var("MODULE_API_PIPELINE_TASK_DATA_BUCKET_NAME")


class HeritabilityReport(DataJobEntity):
  kind = 'heritability_report'
  _blob_prefix = H2_REPORT_PATH_PREFIX
  _input_file  = H2_INPUT_FILE
  _result_file = H2_RESULT_FILE

  _report_display_name = 'Heritability'


  def get_result_path(self):
    return self.get_blob_path()

  def get_input_data_path(self):
    return 'heritability'

  def get_data_directory(self):
    return generate_blob_uri( DATA_BUCKET_NAME, self.get_input_data_path(), schema=BlobURISchema.GS )


  @classmethod
  def get_props_set(cls):
    return {
      *super().get_props_set(),
      'species',
      'label',
      'trait',
    }
