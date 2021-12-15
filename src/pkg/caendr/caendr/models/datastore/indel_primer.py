import os
from logzero import logger

from caendr.models.datastore import Entity


MODULE_SITE_BUCKET_PRIVATE_NAME = os.environ.get('MODULE_SITE_BUCKET_PRIVATE_NAME')
INDEL_REPORT_PATH_PREFIX = 'reports'
INDEL_INPUT_FILE = 'input.json'
INDEL_RESULT_FILE = 'results.tsv'

class IndelPrimer(Entity):
  kind = 'indel_primer'
  __bucket_name = MODULE_SITE_BUCKET_PRIVATE_NAME
  __blob_prefix = INDEL_REPORT_PATH_PREFIX
  __input_file = INDEL_INPUT_FILE
  __result_file = INDEL_RESULT_FILE
  
  def __init__(self, *args, **kwargs):
    super(IndelPrimer, self).__init__(*args, **kwargs)
    self.set_properties(**kwargs)

  def set_properties(self, **kwargs):
    props = self.get_props_set()
    self.__dict__.update((k, v) for k, v in kwargs.items() if k in props)
      
  @classmethod
  def get_bucket_name(cls):
    return cls.__bucket_name
  
  def get_blob_path(self):
    return f'{self.__blob_prefix}/{self.container_name}/{self.data_hash}'
  
  def get_data_blob_path(self):
    return f'{self.get_blob_path()}/{self.__input_file}'
  
  def get_result_blob_path(self):
    return f'{self.get_blob_path()}/{self.__result_file}'
  

  @classmethod
  def get_props_set(cls):
    return {'id',
            'site', 
            'strain1',
            'strain2',
            'data_hash', 
            'username',
            'no_result',
            'container_name',
            'container_version',
            'container_repo',
            'operation_name',
            'status'}
    
  def __repr__(self):
    if hasattr(self, 'id'):
      return f"<{self.kind}:{self.id}>"
    else:
      return f"<{self.kind}:no-id>"
