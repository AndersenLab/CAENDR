import os

from string import Template

from caendr.services.logger import logger

from caendr.models.error import EnvVarError
from caendr.models.datastore import DataJobEntity



MODULE_SITE_BUCKET_PRIVATE_NAME = os.environ.get('MODULE_SITE_BUCKET_PRIVATE_NAME')
INDEL_REPORT_PATH_PREFIX = 'reports'
INDEL_INPUT_FILE = 'input.json'
INDEL_RESULT_FILE = 'results.tsv'


SOURCE_FILENAME = os.environ.get('INDEL_PRIMER_SOURCE_FILENAME')

if not SOURCE_FILENAME:
  raise EnvVarError("INDEL_PRIMER_SOURCE_FILENAME")

SOURCE_FILENAME = Template(SOURCE_FILENAME)



class IndelPrimer(DataJobEntity):
  kind = 'indel_primer'
  __bucket_name = MODULE_SITE_BUCKET_PRIVATE_NAME
  __blob_prefix = INDEL_REPORT_PATH_PREFIX
  __input_file  = INDEL_INPUT_FILE
  __result_file = INDEL_RESULT_FILE


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

  @classmethod
  def get_source_filename(cls, species, release):

    # Validate species
    if species is None:
      raise ValueError('Please provide a species for Indel Primer source filename.')
    # elif species not in SPECIES_LIST.keys():
    #   raise ValueError(f'Cannot construct Indel Primer filename for unknown species "{species}".')

    # Validate release
    if release is None:
      raise ValueError('Please provide a release for Indel Primer source filename.')

    # Fill in template with vars
    return SOURCE_FILENAME.substitute({ 'SPECIES': species, 'RELEASE': release })


  ## All Properties ##

  @classmethod
  def get_props_set(cls):
    return {
      *super(IndelPrimer, cls).get_props_set(),

      # # Status
      # 'no_result',

      # Query
      'site',
      'strain_1',
      'strain_2',

      # Versioning
      'sv_bed_filename',
      'sv_vcf_filename',
      'species',
      'release'
    }
