import os
from enum import Enum

from caendr.utils.env import get_env_var

from caendr.models.datastore import ReportEntity


MODULE_DB_OPERATIONS_BUCKET_NAME = get_env_var('MODULE_DB_OPERATIONS_BUCKET_NAME')


class DbOp(Enum):
  '''
    All possible database operation types.
  '''

  DROP_AND_POPULATE_STRAINS                   = 'DROP_AND_POPULATE_STRAINS'
  DROP_AND_POPULATE_WORMBASE_GENES            = 'DROP_AND_POPULATE_WORMBASE_GENES'
  DROP_AND_POPULATE_STRAIN_ANNOTATED_VARIANTS = 'DROP_AND_POPULATE_STRAIN_ANNOTATED_VARIANTS'
  DROP_AND_POPULATE_ALL_TABLES                = 'DROP_AND_POPULATE_ALL_TABLES'
  TEST_ECHO                                   = 'TEST_ECHO'
  TEST_MOCK_DATA                              = 'TEST_MOCK_DATA'

  def get_title(op):
    '''
      Get the display name for a given operation type.
    '''

    if not op in DbOp:
      raise ValueError()

    titles = {
      DbOp.DROP_AND_POPULATE_STRAINS:                   'Rebuild strain table from google sheet',
      DbOp.DROP_AND_POPULATE_WORMBASE_GENES:            'Rebuild wormbase gene table from external sources',
      DbOp.DROP_AND_POPULATE_STRAIN_ANNOTATED_VARIANTS: 'Rebuild Strain Annotated Variant table from .csv.gz file',
      DbOp.DROP_AND_POPULATE_ALL_TABLES:                'Rebuild All Tables',
      DbOp.TEST_ECHO:                                   'Test ETL - Echo',
      DbOp.TEST_MOCK_DATA:                              'Test ETL - Mock Data',
    }

    return titles.get(op, '???')



class DatabaseOperation(ReportEntity):

  #
  # Class Variables
  #

  kind = 'database_operation'

  _report_display_name = 'Database Operation'

  # Identify the operation by its name
  # This groups executions of the same operation together
  _data_id_field = 'db_operation'


  #
  # Path
  #

  _input_filename  = None
  _output_filename = None

  # TODO: Buckets?

  @property
  def report_bucket_name(self) -> str:
    return MODULE_DB_OPERATIONS_BUCKET_NAME

  @property
  def data_bucket_name(self) -> str:
    return MODULE_DB_OPERATIONS_BUCKET_NAME

  @property
  def work_bucket_name(self) -> str:
    return MODULE_DB_OPERATIONS_BUCKET_NAME


  #
  # Properties
  #

  @classmethod
  def get_props_set(cls):
    return {
      *super().get_props_set(),
      'note',
      'db_operation',
      'args',
      'logs',
    }


  #
  # Database Operation prop
  #

  @property
  def db_operation(self):
    return self.__dict__.get('db_operation', None)

  @db_operation.setter
  def db_operation(self, val):

    # Map string to enum val
    if isinstance(val, str):
      try:
        val = DbOp[val]
      except:
        raise ValueError(f'Cannot set db_operation of {self.kind} job to string "{val}" (not a valid DbOp value)')

    # Check against enum vals
    if not val in DbOp:
      raise TypeError(f'Cannot set db_operation of {self.kind} job to value "{val}" (must be a valid DbOp)')

    # Save as a string value, for easy integration with GCP
    # TODO: Update Entity .save() to work with enums?
    self.__dict__['db_operation'] = val.value


  #
  # Logs prop
  #

  @property
  def logs(self):
    # Prop 'logs' should default to empty string if not set
    return self.__dict__.get('logs', '')

  @logs.setter
  def logs(self, val):
    # Save prop in object's local dictionary
    self.__dict__['logs'] = val
