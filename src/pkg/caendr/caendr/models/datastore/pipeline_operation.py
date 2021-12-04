import os

from caendr.models.datastore import Entity

class PipelineOperation(Entity):
  kind = 'pipeline_operation'
  
  def __init__(self, *args, **kwargs):
    super(PipelineOperation, self).__init__(*args, **kwargs)
    self.set_properties(**kwargs)

  def set_properties(self, **kwargs):
    props = self.get_props_set()
    self.__dict__.update((k, v) for k, v in kwargs.items() if k in props)
      
  @classmethod
  def get_props_set(cls):
    return {'id',
            'operation',
            'data_hash',
            'metadata',
            'report_path',
            'error',
            'done'}
    
  def __repr__(self):
    if hasattr(self, 'id'):
      return f"<{self.kind}:{self.id}>"
    else:
      return f"<{self.kind}:no-id>"
