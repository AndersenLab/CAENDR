from logzero import logger



class Task(object):
  name = 'task'

  def __init__(self, *args, **kwargs):

    # Set properties from keyword arguments
    self.set_properties(**kwargs)

  def set_properties(self, **kwargs):
    props = self.get_props_set()
    self.__dict__.update((k, v) for k, v in kwargs.items() if k in props)

  @classmethod
  def get_props_set(cls):
    return {
      'id',
      'kind',
      'username',
      'container_name',
      'container_version',
      'container_repo',
    }

  def get_payload(self):
    return { k: self.__getattribute__(k) for k in self.get_props_set() }

  def __repr__(self):
    return f"<{self.name}:{getattr(self, 'id', 'no-id')}>"



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



class NemaScanTask(Task):
  name = 'nemascan_task'

  @classmethod
  def get_props_set(cls):
    return {
      *super(NemaScanTask, cls).get_props_set(),
      'data_hash',
      'species',
    }



class DatabaseOperationTask(Task):
  name = 'db_op_task'

  @classmethod
  def get_props_set(cls):
    return {
      *super(DatabaseOperationTask, cls).get_props_set(),
      'email',
      'db_operation',
      'args',
    }



class IndelPrimerTask(Task):
  name  = 'indel_primer_task'

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



class HeritabilityTask(Task):
  name = 'heritability_task'
  
  @classmethod
  def get_props_set(cls):
    return {
      *super(HeritabilityTask, cls).get_props_set(),
      'data_hash',
    }



class GeneBrowserTracksTask(Task):
  name = 'gene_browser_tracks_task'

  @classmethod
  def get_props_set(cls):
    return {
      *super(GeneBrowserTracksTask, cls).get_props_set(),
      'wormbase_version',
    }
