import os

from caendr.models.datastore import Entity

class PipelineOperation(Entity):
  kind = 'pipeline_operation'

  @classmethod
  def get_props_set(cls):
    return {
      *super().get_props_set(),
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



class PipelineOperationStatus(Entity):

  @classmethod
  def get_props_set(cls):
    return {
      *super().get_props_set(),
      'status'
    }

  def __repr__(self):
    return f"<PipelineOperationStatus:{getattr(self, 'id', 'no-id')}>"
