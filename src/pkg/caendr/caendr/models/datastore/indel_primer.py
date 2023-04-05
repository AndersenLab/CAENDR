import os

from string import Template

from caendr.services.logger import logger
from caendr.utils.env import get_env_var

from caendr.models.error import EnvVarError
from caendr.models.datastore import DataJobEntity



INDEL_REPORT_PATH_PREFIX = 'reports'
INDEL_INPUT_FILE = 'input.json'
INDEL_RESULT_FILE = 'results.tsv'

# Get environment variables
MODULE_SITE_BUCKET_PUBLIC_NAME = get_env_var('MODULE_SITE_BUCKET_PUBLIC_NAME')
SOURCE_FILENAME = get_env_var('INDEL_PRIMER_SOURCE_FILENAME')

SOURCE_FILENAME = Template(SOURCE_FILENAME.replace('{', '${'))



class IndelPrimer(DataJobEntity):
  kind = 'indel_primer'
  _blob_prefix = INDEL_REPORT_PATH_PREFIX
  _input_file  = INDEL_INPUT_FILE
  _result_file = INDEL_RESULT_FILE


  ## Bucket ##

  # TODO: Indel primer results currently don't have subdirectories for container versions. Should they?
  def get_blob_path(self):
    return f'{self._blob_prefix}/{self.container_name}/{self.data_hash}'


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


  @staticmethod
  def get_fasta_filepath(species, release = None):
    from caendr.models.datastore import SPECIES_LIST
    species_obj = SPECIES_LIST[species]

    # Default to the latest version defined for the species
    if release is None:
      release = species_obj['indel_primer_ver']

    # TODO: Look up these values using release version
    species_prj = species_obj['project_num']
    species_wb  = species_obj['wb_ver']

    # Return filepath
    return {
      'bucket': MODULE_SITE_BUCKET_PUBLIC_NAME,
      'path': ('dataset_release', species, release, 'browser_tracks'),
      'name': f'{ species }.{ species_prj }.{ species_wb }.genome',
      'ext':  '.fa',
    }


  ## All Properties ##

  @classmethod
  def get_props_set(cls):
    return {
      *super().get_props_set(),

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
