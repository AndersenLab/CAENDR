import os
from caendr.services.logger import logger

from caendr.models.datastore import JobEntity


MODULE_SITE_BUCKET_PRIVATE_NAME = os.environ.get('MODULE_SITE_BUCKET_PRIVATE_NAME')
NEMASCAN_REPORT_PATH_PREFIX = 'reports'
NEMASCAN_RESULT_PATH_INFIX = 'results'
INPUT_DATA_PATH = 'tools/nemascan/input_data'
REPORT_DATA_PREFIX = 'Reports/NemaScan_Report_'
NEMASCAN_INPUT_FILE = 'data.tsv'


class NemascanMapping(JobEntity):
  kind = 'nemascan_mapping'
  __bucket_name = MODULE_SITE_BUCKET_PRIVATE_NAME
  __blob_prefix = NEMASCAN_REPORT_PATH_PREFIX
  __result_infix = NEMASCAN_RESULT_PATH_INFIX
  __input_data_path = INPUT_DATA_PATH
  __input_file = NEMASCAN_INPUT_FILE
  __report_path = REPORT_DATA_PREFIX


  @classmethod
  def get_bucket_name(cls):
    return cls.__bucket_name

  def get_blob_path(self):
    return f'{self.__blob_prefix}/{self.container_name}/{self.container_version}/{self.data_hash}'

  def get_data_blob_path(self):
    return f'{self.get_blob_path()}/{self.__input_file}'

  def get_result_path(self):
    return f'{self.get_blob_path()}/{self.__result_infix}'

  def get_report_blob_prefix(self):
    return f'{self.get_result_path()}/{self.__report_path}'

  def get_input_data_path(self):
    return f'{self.__input_data_path}'


  @classmethod
  def get_props_set(cls):
    return {
      *super(NemascanMapping, cls).get_props_set(),

      # Submission
      'id',
      'data_hash',
      'username',
      'email',

      # Query
      'label',
      'trait',
      'report_path',
    }

  def __repr__(self):
    return f"<{self.kind}:{getattr(self, 'id', 'no-id')}>"
