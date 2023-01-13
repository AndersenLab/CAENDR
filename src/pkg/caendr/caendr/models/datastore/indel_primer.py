import os
from logzero import logger

from caendr.models.datastore import JobEntity



MODULE_SITE_BUCKET_PRIVATE_NAME = os.environ.get('MODULE_SITE_BUCKET_PRIVATE_NAME')
INDEL_REPORT_PATH_PREFIX = 'reports'
INDEL_INPUT_FILE = 'input.json'
INDEL_RESULT_FILE = 'results.tsv'


class IndelPrimer(JobEntity):
  kind = 'indel_primer'
  __bucket_name = MODULE_SITE_BUCKET_PRIVATE_NAME
  __blob_prefix = INDEL_REPORT_PATH_PREFIX
  __input_file  = INDEL_INPUT_FILE
  __result_file = INDEL_RESULT_FILE


  def __repr__(self):
    return f"<{self.kind}:{getattr(self, 'id', 'no-id')}>"


  ## Bucket ##

  @classmethod
  def get_bucket_name(cls):
    return cls.__bucket_name
  
  def get_blob_path(self):
    return f'{self.__blob_prefix}/{self.container_name}/{self.data_hash}'
  
  def get_data_blob_path(self):
    return f'{self.get_blob_path()}/{self.__input_file}'
  
  def get_result_blob_path(self):
    return f'{self.get_blob_path()}/{self.__result_file}'


  ## All Properties ##

  @classmethod
  def get_props_set(cls):
    return {
      *super(IndelPrimer, cls).get_props_set(),

      # Submission
      'id',
      'data_hash',
      'username',
      'operation_name',

      # # Status
      # 'no_result',

      # Query
      'site',
      'strain_1',
      'strain_2',

      # Files
      'sv_bed_filename',
      'sv_vcf_filename',
    }
