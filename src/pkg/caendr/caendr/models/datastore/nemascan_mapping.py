import os
from caendr.services.logger import logger

from caendr.models.datastore import DataJobEntity


MODULE_SITE_BUCKET_PRIVATE_NAME = os.environ.get('MODULE_SITE_BUCKET_PRIVATE_NAME')
NEMASCAN_REPORT_PATH_PREFIX = 'reports'
NEMASCAN_RESULT_PATH_INFIX = 'results'
INPUT_DATA_PATH = 'tools/nemascan/input_data'
REPORT_DATA_PREFIX = 'Reports/NemaScan_Report_'
NEMASCAN_INPUT_FILE = 'data.tsv'


class NemascanMapping(DataJobEntity):
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
      *super().get_props_set(),

      # Submission
      'email',

      # Query
      'species',
      'label',
      'trait',
      'report_path',
    }

  # TODO: Is there a better way to check? E.g. look for results?
  # TODO: Propagate the status of the found Entity to the submission check. Prefer status = "COMPLETE"?
  def check_cached_result(self):

    # Check for reports with a matching data hash & container version
    matches = NemascanMapping.query_ds( filters = [
      ('data_hash',         '=', self.data_hash),
      ('container_version', '=', self['container_version']),
    ])

    # If any submission was found from a different user, return it
    for match in matches:
      if match.username != self.username:
        return match
