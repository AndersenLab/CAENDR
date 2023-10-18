from caendr.services.logger import logger

from caendr.models.datastore import DataJobEntity
from caendr.models.status import JobStatus
from caendr.services.cloud.storage import check_blob_exists, get_blob_list


NEMASCAN_REPORT_PATH_PREFIX = 'reports'
NEMASCAN_RESULT_PATH_INFIX = 'results'
INPUT_DATA_PATH = 'tools/nemascan/input_data'
REPORT_DATA_PREFIX = 'Reports/NemaScan_Report_'
NEMASCAN_INPUT_FILE = 'data.tsv'


class NemascanReport(DataJobEntity):
  kind = 'nemascan_mapping'
  _blob_prefix = NEMASCAN_REPORT_PATH_PREFIX
  _input_file  = NEMASCAN_INPUT_FILE

  _report_display_name = 'Genetic Mapping'

  __result_infix = NEMASCAN_RESULT_PATH_INFIX
  __input_data_path = INPUT_DATA_PATH
  __report_path = REPORT_DATA_PREFIX


  ## Buckets & Paths ##

  # TODO: Overrides function in DataJobEntity parent class which isn't needed in this class.
  #       Can this be merged with get_result_path for better inheritance?
  def get_result_blob_path(self):
    raise TypeError(f'Should not call get_result_blob_path on {self.__class__.__name__}')

  def get_result_path(self):
    return f'{self.get_blob_path()}/{self.__result_infix}'

  def get_report_blob_prefix(self):
    return f'{self.get_result_path()}/{self.__report_path}'

  def get_input_data_path(self):
    return f'{self.__input_data_path}'

  def get_data_directory(self):
    return f"gs://{ self.get_bucket_name() }/{ self.get_input_data_path() }"


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

    # Check if this value has been cached already, and if so, make sure the file exists
    path = self._get_meta_prop('report_path')
    if path is not None:
      if check_blob_exists(self.get_bucket_name(), path):
        return path
      else:
        logger.warn(f'Genetic Mapping report {self.id} lists its report path as "{path}", but this file does not exist. Recomputing...')

    # If job threw an error, don't search for report path
    if self['status'] == JobStatus.ERROR:
      logger.warn(f'Trying to compute report path for Genetic Mapping report "{self.id}", but job returned an error. Returning None.')
      return None

    # Get a list of all files with this report's prefix
    logger.debug(f'Looking for a Genetic Mapping HTML report for ID "{self.id}"')
    result = list(get_blob_list(self.get_bucket_name(), self.get_report_blob_prefix()))
    logger.debug(result)

    # Search the list for an HTML file, and return it if found
    # Implicitly returns None if no such file is found
    for file in result:
      logger.debug(file.name)
      if file.name.endswith('.html'):
        self._set_meta_prop('report_path', file.name)
        return file.name


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
    matches = NemascanReport.query_ds( filters = [
      ('data_hash',         '=', self.data_hash),
      ('container_version', '=', self['container_version']),
    ])

    status = None

    # Loop through all submissions by different users
    for match in matches:
      if match.username != self.username:

        # Update to match status, keeping 'COMPLETE' if it's found
        if status != JobStatus.COMPLETE:
          status = match.status

    # Return the status
    return status
