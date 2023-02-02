import os

from caendr.models.datastore import Entity

class PipelineOperation(Entity):
  kind = 'pipeline_operation'

  @classmethod
  def get_props_set(cls):
    return {
      *super(PipelineOperation, cls).get_props_set(),
      'id',
      'operation',
      'operation_kind',
      'data_hash',
      'metadata',
      'report_path',
      'error',
      'email',
      'username',
      'done'
    }

  def __repr__(self):
    return f"<{self.kind}:{getattr(self, 'id', 'no-id')}>"



class PipelineOperationStatus(Entity):

  @classmethod
  def get_props_set(cls):
    return {
      *super(PipelineOperationStatus, cls).get_props_set(),
      'status'
    }

  def __repr__(self):
    return f"<PipelineOperationStatus:{getattr(self, 'id', 'no-id')}>"
