import os

from logzero import logger

from caendr.models.datastore import Entity

from caendr.services.cloud.secret import get_secret
from caendr.services.cloud.task   import add_task


MODULE_API_PIPELINE_TASK_URL_NAME = os.environ.get('MODULE_API_PIPELINE_TASK_URL_NAME')
API_PIPELINE_TASK_URL = get_secret(MODULE_API_PIPELINE_TASK_URL_NAME)



class Task(object):
  name  = 'task'
  queue = None


  ## Initialization ##

  def __init__(self, source_obj: Entity = None, **kwargs):
    '''
      Args:
        source_obj (Entity, optional): An Entity to initialize from.
    '''

    # Initialize props from source Entity, if one is provided
    if source_obj is not None:
      self.kind = source_obj.__class__.kind
      self.set_properties( **dict(source_obj) )

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
    return add_task( self.queue, self.queue_url, dict(self) )



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



class DatabaseOperationTask(Task):
  name  = 'db_op_task'
  queue = os.environ.get('MODULE_DB_OPERATIONS_TASK_QUEUE_NAME')

  @classmethod
  def get_props_set(cls):
    return {
      *super(DatabaseOperationTask, cls).get_props_set(),
      'email',
      'db_operation',
      'args',
    }



class GeneBrowserTracksTask(Task):
  name  = 'gene_browser_tracks_task'
  queue = os.environ.get('MODULE_GENE_BROWSER_TRACKS_TASK_QUEUE_NAME')

  @classmethod
  def get_props_set(cls):
    return {
      *super(GeneBrowserTracksTask, cls).get_props_set(),
      'wormbase_version',
    }



class HeritabilityTask(Task):
  name  = 'heritability_task'
  queue = os.environ.get('HERITABILITY_TASK_QUEUE_NAME')

  @classmethod
  def get_props_set(cls):
    return {
      *super(HeritabilityTask, cls).get_props_set(),
      'data_hash',
    }



class IndelPrimerTask(Task):
  name  = 'indel_primer_task'
  queue = os.environ.get('INDEL_PRIMER_TASK_QUEUE_NAME')

  @classmethod
  def get_props_set(cls):
    return {
      *super(IndelPrimerTask, cls).get_props_set(),
      'data_hash',
      'site',
      'strain_1',
      'strain_2',
      'sv_bed_filename',
      'sv_vcf_filename',
    }



class NemaScanTask(Task):
  name  = 'nemascan_task'
  queue = os.environ.get('NEMASCAN_TASK_QUEUE_NAME')

  @classmethod
  def get_props_set(cls):
    return {
      *super(NemaScanTask, cls).get_props_set(),
      'data_hash',
      'species',
    }
