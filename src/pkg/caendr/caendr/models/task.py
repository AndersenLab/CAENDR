import os

from caendr.services.logger import logger

from caendr.models.datastore import Entity, DatabaseOperation, HeritabilityReport, IndelPrimerReport, NemascanReport

from caendr.services.cloud.secret import get_secret
from caendr.services.cloud.task   import add_task
from caendr.utils.env             import get_env_var


MODULE_API_PIPELINE_TASK_URL_NAME = get_env_var('MODULE_API_PIPELINE_TASK_URL_NAME')
API_PIPELINE_TASK_URL = get_secret(MODULE_API_PIPELINE_TASK_URL_NAME)



## Task Superclass Definition ##

# Define the Status values
class TaskStatus:

  # Basic TaskStatus values
  CREATED   = "CREATED"
  ERROR     = "ERROR"
  RUNNING   = "RUNNING"
  COMPLETE  = "COMPLETE"
  SUBMITTED = "SUBMITTED"

  # Meaningful sets of TaskStatus values
  FINISHED  = { COMPLETE, ERROR }
  NOT_ERR   = { SUBMITTED, RUNNING, COMPLETE }

  # Check whether a variable is a valid TaskStatus
  @staticmethod
  def is_valid(value):
    return value in {
      TaskStatus.CREATED,
      TaskStatus.ERROR,
      TaskStatus.RUNNING,
      TaskStatus.COMPLETE,
      TaskStatus.SUBMITTED,
    }



class Task(object):

  # A human readable name for this Task type
  # Should be overwritten in subclasses
  name = 'task'

  # The name of the queue that handles Tasks of this type
  # Should be overwritten in subclasses
  queue = None

  # The kind of Entity associated with this Task type
  # Should be overwritten in subclasses
  kind = None


  ## Initialization ##

  def __init__(self, source_obj: Entity = None, **kwargs):
    '''
      Args:
        source_obj (Entity, optional): An Entity to initialize from.
    '''

    # Initialize props from source Entity, if one is provided
    if source_obj is not None:

      # If subclass does not specify a kind, it cannot be initialized from an Entity
      if self.kind is None:
        raise ValueError(f'Cannot initialize Task of type "{self.name}" from Entity.')

      # Check that kind of subclass matches kind of Entity to init from
      if self.kind != source_obj.__class__.kind:
        raise ValueError(
          f'Cannot initialize Task of type "{self.name}" from Entity of kind "{source_obj.__class__.kind}" (expected "{self.kind}").'
        )

      # If all checks passed, copy the properties of the source Entity
      self.set_properties(**dict(source_obj))
      self.set_properties(id = source_obj.id)

    # Set properties from keyword arguments
    self.set_properties(**kwargs)


  def set_properties(self, **kwargs):
    '''
      Set multiple properties using keyword arguments.
      Only properties specified in get_props_set() will be accepted.
    '''
    props = self.get_props_set()
    self.__dict__.update((k, v) for k, v in kwargs.items() if k in props)


  def __repr__(self):
    return f"<{self.name}:{getattr(self, 'id', 'no-id')}>"


  ## Property List ##

  @classmethod
  def get_props_set(cls):
    '''
      Define the set of properties for a task.
      This set should be extended in subclasses.
    '''
    return {
      'id',
      'kind',
      'username',
      'container_name',
      'container_version',
      'container_repo',
    }


  def __iter__(self):
    '''
      Iterate through all props in the task.

      Returns all attributes saved in this object's __dict__ field, with keys
      present in the props set.

      Allows conversion to dictionary via dict().
    '''
    return ( ( k, self.__getattribute__(k) ) for k in self.get_props_set() )


  ## Task Submission ##

  @property
  def queue_url(self):
    '''
      URL of the queue that handles tasks of this type.
    '''
    return f'{API_PIPELINE_TASK_URL}/task/start/{self.queue}'


  def submit(self):
    '''
      Submit this task to the appropriate queue.
      Uses dictionary of fields -> values as payload.
    '''
    if self.queue is None:
      raise ValueError(f'Target queue is undefined for task of type "{self.name}".')

    return add_task( self.queue, self.queue_url, dict(self) )



## Test Tasks ##


class EchoTask(Task):
  name = 'echo_task'

  @classmethod
  def get_props_set(cls):
    return {
      *super(EchoTask, cls).get_props_set(),
      'data_hash',
    }


class MockDataTask(Task):
  name = 'mock_data_task'

  @classmethod
  def get_props_set(cls):
    return {
      *super(MockDataTask, cls).get_props_set(),
      'data_hash',
    }



## Job Tasks ##


class DatabaseOperationTask(Task):
  name  = 'db_op_task'
  queue = os.environ.get('MODULE_DB_OPERATIONS_TASK_QUEUE_NAME')
  kind  = DatabaseOperation.kind

  @classmethod
  def get_props_set(cls):
    return {
      *super().get_props_set(),
      'email',
      'db_operation',
      'args',
    }


class HeritabilityTask(Task):
  name  = 'heritability_task'
  queue = os.environ.get('HERITABILITY_TASK_QUEUE_NAME')
  kind  = HeritabilityReport.kind

  @classmethod
  def get_props_set(cls):
    return {
      *super().get_props_set(),
      'data_hash',
      'species'
    }


class IndelPrimerTask(Task):
  name  = 'indel_primer_task'
  queue = os.environ.get('INDEL_PRIMER_TASK_QUEUE_NAME')
  kind  = IndelPrimerReport.kind

  @classmethod
  def get_props_set(cls):
    return {
      *super().get_props_set(),
      'data_hash',
      'site',
      'strain_1',
      'strain_2',
      'sv_bed_filename',
      'sv_vcf_filename',
      'species',
      'release',
    }


class NemascanTask(Task):
  name  = 'nemascan_task'
  queue = os.environ.get('NEMASCAN_TASK_QUEUE_NAME')
  kind  = NemascanReport.kind

  @classmethod
  def get_props_set(cls):
    return {
      *super().get_props_set(),
      'data_hash',
      'species',
    }
