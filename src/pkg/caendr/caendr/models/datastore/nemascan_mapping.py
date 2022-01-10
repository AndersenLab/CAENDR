import os
from logzero import logger

from caendr.models.datastore import Entity


MODULE_SITE_BUCKET_PRIVATE_NAME = os.environ.get('MODULE_SITE_BUCKET_PRIVATE_NAME')
NEMASCAN_REPORT_PATH_PREFIX = 'reports'
NEMASCAN_RESULT_PATH_INFIX = 'results'
INPUT_DATA_PATH = 'tools/nemascan/input_data'
REPORT_DATA_PREFIX = 'Reports/NemaScan_Report_'
NEMASCAN_INPUT_FILE = 'data.tsv'

class NemascanMapping(Entity):
  kind = 'nemascan_mapping'
  __bucket_name = MODULE_SITE_BUCKET_PRIVATE_NAME
  __blob_prefix = NEMASCAN_REPORT_PATH_PREFIX
  __result_infix = NEMASCAN_RESULT_PATH_INFIX
  __input_data_path = INPUT_DATA_PATH
  __input_file = NEMASCAN_INPUT_FILE
  __report_path = REPORT_DATA_PREFIX
  
  def __init__(self, *args, **kwargs):
    super(NemascanMapping, self).__init__(*args, **kwargs)
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
  
  def get_result_path(self):
    return f'{self.get_blob_path()}/{self.__result_infix}'

  def get_report_blob_prefix(self):
    return f'{self.get_result_path()}/{self.__report_path}'
  
  def get_input_data_path(self):
    return f'{self.__input_data_path}'

  @classmethod
  def get_props_set(cls):
    return {'id',
            'label', 
            'trait', 
            'data_hash', 
            'username',
            'report_path',
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
