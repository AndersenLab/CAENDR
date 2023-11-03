import os

from caendr.services.logger import logger
from caendr.utils.env import get_env_var

from caendr.models.datastore import ReportEntity, HashableEntity, Species
from caendr.services.dataset_release import get_dataset_release



# Get environment variables
MODULE_SITE_BUCKET_PUBLIC_NAME = get_env_var('MODULE_SITE_BUCKET_PUBLIC_NAME')
SOURCE_FILENAME                = get_env_var('INDEL_PRIMER_SOURCE_FILENAME', as_template=True)



class IndelPrimerReport(HashableEntity, ReportEntity):

  #
  # Class variables
  #

  kind = 'indel_primer'

  _report_display_name = 'Primer'

  # Identify the report data by the data hash, inherited from the HashableEntity parent class
  _data_id_field = 'data_hash'


  #
  # Path
  #

  # TODO: Indel primer results currently don't have subdirectories for container versions. Should they?
  @property
  def _report_prefix(self):
    return '/'.join([ self._report_path_prefix(), self.container_name, self.get_data_id() ])


  #
  # Input & Output
  #

  _num_input_files = 1
  _input_filename  = 'input.json'
  _output_filename = 'results.tsv'


  #
  # Data Files
  #

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
    return SOURCE_FILENAME.get_string(**{
      'SPECIES': species,
      'RELEASE': release,
    })


  @staticmethod
  def get_fasta_filepath(species, release = None):
    '''
      Uses the provided release, or looks up the most recent release supporting Indel Primer
      for the given species.

      Equivalent to running `get_fasta_filepath_obj` on the appropriate DatasetRelease object.
    '''

    # Lookup desired species object
    species_obj = Species.from_name(species)

    # Default to the latest version defined for the species
    if release is None:
      release = species_obj['release_pif']

    # Get DatasetRelease object and use to construct the FASTA filepath
    release_obj = get_dataset_release(release)
    return release_obj.get_fasta_filepath_obj()


  #
  # Properties
  #

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
