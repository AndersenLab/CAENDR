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

  def __getitem__(self, prop):

    # Prop 'logs' should default to empty string if not set
    if prop == 'logs':
      return self.__dict__.get(prop, '')

    # Use default for other props
    return super().__getitem__(prop)

  def __repr__(self):
    return f"<{self.kind}:{getattr(self, 'id', 'no-id')}>"
