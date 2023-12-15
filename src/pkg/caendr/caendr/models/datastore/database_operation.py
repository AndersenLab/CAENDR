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
  DROP_AND_POPULATE_PHENOTYPE_DB              = 'DROP_AND_POPULATE_PHENOTYPE_DB'
  DROP_AND_POPULATE_ALL_TABLES                = 'DROP_AND_POPULATE_ALL_TABLES'
  POPULATE_PHENOTYPES_DATASTORE               = 'POPULATE_PHENOTYPES_DATASTORE'
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
      DbOp.DROP_AND_POPULATE_PHENOTYPE_DB:              'Rebuild Phenotype Database table from datastore file records',
      DbOp.DROP_AND_POPULATE_ALL_TABLES:                'Rebuild All Tables',
      DbOp.POPULATE_PHENOTYPES_DATASTORE:               'Create / update datastore trait file records from Google Sheet',
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

  # TODO: Buckets?

  @property
  def _report_bucket(self) -> str:
    return MODULE_DB_OPERATIONS_BUCKET_NAME

  @property
  def _data_bucket_name(self) -> str:
    return MODULE_DB_OPERATIONS_BUCKET_NAME

  @property
  def _work_bucket_name(self) -> str:
    return MODULE_DB_OPERATIONS_BUCKET_NAME


  #
  # Input & Output
  #

  _num_input_files = 0
  _input_filename  = None
  _output_filename = None


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
    return self._get_enum_prop(DbOp, 'db_operation', None)

  @db_operation.setter
  def db_operation(self, val):
    return self._set_enum_prop(DbOp, 'db_operation', val)


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
