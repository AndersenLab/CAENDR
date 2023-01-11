import os
from caendr.services.logger import logger

from caendr.models.datastore import Entity


MODULE_SITE_BUCKET_PRIVATE_NAME = os.environ.get('MODULE_SITE_BUCKET_PRIVATE_NAME')
H2_REPORT_PATH_PREFIX = 'reports'
H2_INPUT_FILE = 'data.tsv'
H2_RESULT_FILE = 'heritability_result.tsv'

class HeritabilityReport(Entity):
  kind = 'heritability_report'
  __bucket_name = MODULE_SITE_BUCKET_PRIVATE_NAME
  __blob_prefix = H2_REPORT_PATH_PREFIX
  __input_file = H2_INPUT_FILE
  __result_file = H2_RESULT_FILE
  
  def __init__(self, *args, **kwargs):
    super(HeritabilityReport, self).__init__(*args, **kwargs)
    self.set_properties(**kwargs)

  def set_properties(self, **kwargs):
    props = self.get_props_set()
    self.__dict__.update((k, v) for k, v in kwargs.items() if k in props)
  
  @classmethod
  def get_bucket_name(cls):
    return cls.__bucket_name
  
  def get_blob_path(self):
    return f'{self.__blob_prefix}/{self.container_name}/{self.container_version}/{self.data_hash}'
  
  def get_data_blob_path(self):
    return f'{self.get_blob_path()}/{self.__input_file}'
  
  def get_result_blob_path(self):
    return f'{self.get_blob_path()}/{self.__result_file}'
  

  @classmethod
  def get_props_set(cls):
    return {'id',
            'label',
            'data_hash',
            'trait',
            'username',
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
