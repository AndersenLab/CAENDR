from caendr.utils.env import get_env_var

from caendr.models.datastore import ReportEntity
from caendr.models.sql       import DbOp


MODULE_DB_OPERATIONS_BUCKET_NAME = get_env_var('MODULE_DB_OPERATIONS_BUCKET_NAME')



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
