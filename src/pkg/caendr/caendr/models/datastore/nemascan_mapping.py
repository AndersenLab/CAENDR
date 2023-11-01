from caendr.services.logger import logger

from caendr.models.datastore import HashableEntity, ReportEntity
from caendr.models.status import JobStatus
from caendr.services.cloud.storage import BlobURISchema, generate_blob_uri, check_blob_exists, get_blob_list


REPORT_DATA_PREFIX = 'Reports/NemaScan_Report_'



class NemascanReport(HashableEntity, ReportEntity):

  #
  # Class Variables
  #

  kind = 'nemascan_mapping'

  _report_display_name = 'Genetic Mapping'

  # Identify the report data by the data hash, inherited from the HashableEntity parent class
  _data_id_field = 'data_hash'


  #
  # Paths
  #

  @property
  def _data_prefix(self):
    return 'tools/nemascan/input_data'

  @property
  def _output_prefix(self):
    return 'results'

  def get_data_paths(self, schema: BlobURISchema):
    return {
      **super().get_data_paths(schema=schema),
      'TRAIT_FILE': self.input_filepath(schema=schema),
    }


  #
  # Input & Output
  #

  _input_filename  = 'data.tsv'

  # Use report_path property to get the filename of the report within the output directory
  @property
  def _output_filename(self):
    report_path   = self.report_path
    report_prefix = self.output_directory(schema=BlobURISchema.PATH)[1]
    if report_path and report_path.startswith(report_prefix):
      report_path = report_path[len(report_prefix):].lstrip('/')
    return report_path

  def upload(self, *data_files):
    if len(data_files) != 1:
      raise ValueError(f'Exactly one data file should be uploaded for job of type {self.kind}')
    return super().upload(*data_files)


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
      if check_blob_exists(self._report_bucket, path):
        return path
      else:
        logger.warn(f'Genetic Mapping report {self.id} lists its report path as "{path}", but this file does not exist. Recomputing...')

    # If job threw an error, don't search for report path
    if self['status'] == JobStatus.ERROR:
      logger.warn(f'Trying to compute report path for Genetic Mapping report "{self.id}", but job returned an error. Returning None.')
      return None

    # Get a list of all files with this report's prefix
    logger.debug(f'Looking for a Genetic Mapping HTML report for ID "{self.id}"')
    result = get_blob_list( *self.output_directory(REPORT_DATA_PREFIX, schema=BlobURISchema.PATH) )
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
