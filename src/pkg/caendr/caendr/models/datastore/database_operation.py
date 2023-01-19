import os

from caendr.models.datastore import JobEntity


MODULE_DB_OPERATIONS_BUCKET_NAME = os.environ.get('MODULE_DB_OPERATIONS_BUCKET_NAME')


class DatabaseOperation(JobEntity):
  kind = 'database_operation'
  __bucket_name = MODULE_DB_OPERATIONS_BUCKET_NAME

  @classmethod
  def get_bucket_name(cls):
    return cls.__bucket_name

  @classmethod
  def get_props_set(cls):
    return {
      *super(DatabaseOperation, cls).get_props_set(),

      # Submission
      'id',
      'username',
      'email',

      # Other
      'note',
      'db_operation',
      'args',
      'logs',
    }

  def __repr__(self):
    return f"<{self.kind}:{getattr(self, 'id', 'no-id')}>"



  ## Special Properties ##

  @property
  def logs(self):
    # Prop 'logs' should default to empty string if not set
    return self.__dict__.get('logs', '')

  @logs.setter
  def logs(self, val):
    # Save prop in object's local dictionary
    self.__dict__['logs'] = val
