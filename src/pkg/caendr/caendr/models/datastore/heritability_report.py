import os

from caendr.models.datastore import DataJobEntity


MODULE_SITE_BUCKET_PRIVATE_NAME = os.environ.get('MODULE_SITE_BUCKET_PRIVATE_NAME')
H2_REPORT_PATH_PREFIX = 'reports'
H2_INPUT_FILE = 'data.tsv'
H2_RESULT_FILE = 'heritability_result.tsv'


class HeritabilityReport(DataJobEntity):
  kind = 'heritability_report'
  __bucket_name = MODULE_SITE_BUCKET_PRIVATE_NAME
  __blob_prefix = H2_REPORT_PATH_PREFIX
  __input_file  = H2_INPUT_FILE
  __result_file = H2_RESULT_FILE


  @classmethod
  def get_bucket_name(cls):
    return cls.__bucket_name

  def get_blob_path(self):
    return f'{self.__blob_prefix}/{self.container_name}/{self.container_version}/{self.data_hash}'

  def get_data_blob_path(self):
    return f'{self.get_blob_path()}/{self.__input_file}'

  def get_result_blob_path(self):
    return f'{self.get_blob_path()}/{self.__result_file}'


  @classmethod
  def get_props_set(cls):
    return {
      *super().get_props_set(),

      # Query
      'label',
      'trait',
    }
