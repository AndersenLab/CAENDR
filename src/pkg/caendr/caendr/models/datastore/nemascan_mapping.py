import os
from caendr.services.logger import logger

from caendr.models.datastore import DataJobEntity
from caendr.services.cloud.storage import get_blob_list


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


  ## Properties List ##

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
    }

  @classmethod
  def get_props_set_meta(cls):
    return {
      *super().get_props_set_meta(),
      'report_path',
    }


  ## Meta Properties ##

  @property
  def report_path(self):
    path = self._get_meta_prop('report_path')
    if path is not None:
      return path

    # TODO: Don't try to compute if status is ERROR??

    logger.debug(f'Looking for a NemaScan Mapping HTML report: {self.id}')

    result = list(get_blob_list(self.get_bucket_name(), self.get_report_blob_prefix()))
    logger.debug(result)

    for file in result:
      logger.debug(file.name)
      if file.name.endswith('.html'):
        self._set_meta_prop('report_path', file.name)
        return file.name


  @report_path.setter
  def report_path(self, val):
    self._set_meta_prop('report_path', val)


  ## User Object ##

  def set_user(self, user):
    '''
      Set user properties from a User object.
      Sets username and email to match provided user.
    '''
    self['email'] = user['email']
    return super().set_user(user)


  ## Cache ##

  # TODO: Is there a better way to check? E.g. look for results?
  def check_cached_result(self):
    '''
      Check whether the results for this data hash have already been cached.
      Returns "COMPLETE" if any other user's submission is complete, otherwise
      returns the last found status or None.
    '''

    # Check for reports with a matching data hash & container version
    matches = NemascanMapping.query_ds( filters = [
      ('data_hash',         '=', self.data_hash),
      ('container_version', '=', self['container_version']),
    ])

    status = None

    # Loop through all submissions by different users
    for match in matches:
      if match.username != self.username:

        # Update to match status, keeping 'COMPLETE' if it's found
        if status != 'COMPLETE':
          status = match.status

    # Return the status
    return status
