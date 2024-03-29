import os
from typing import Union, Tuple

from caendr.services.logger import logger

from caendr.api.gene import remove_prefix
from caendr.models.datastore import Species, SpeciesEntity
from caendr.models.error import NotFoundError
from caendr.services.cloud.storage import BlobURISchema, generate_blob_uri, get_blob_list, check_blob_exists
from caendr.utils.env import get_env_var, get_env_var_with_fallback
from caendr.utils.tokens import TokenizedString



V1_V2_Cutoff_Date = 20200101

DATASET_RELEASE_BUCKET_NAME = get_env_var_with_fallback('MODULE_SITE_BUCKET_DATASET_RELEASE_NAME', 'MODULE_SITE_BUCKET_PUBLIC_NAME')

FASTA_FILENAME_TEMPLATE = get_env_var('FASTA_FILENAME_TEMPLATE', as_template=True)
FASTA_EXTENSION_FILE    = get_env_var('FASTA_EXTENSION_FILE')
FASTA_EXTENSION_INDEX   = get_env_var('FASTA_EXTENSION_INDEX')



class ReportType():
  __all_report_types = {}

  def __init__(self, name, data_map, cutoff_date=None):
    self.name = name
    self.data_map = data_map
    self.cutoff_date = cutoff_date

    ReportType.__all_report_types[name] = self

  @classmethod
  def lookup(cls, name, fallback=None):
    return cls.__all_report_types.get(name, fallback)

  def __eq__(self, other):
    if isinstance(other, str):
      return self.name == other
    elif isinstance(other, ReportType):
      return self.name == other.name
    else:
      raise TypeError()

  def get_data_map(self):
    return self.data_map

  def version_meets_cutoff(self, version):
    return int(version) >= (self.cutoff_date or 0)

  def __repr__(self):
    return f"<ReportType:{getattr(self, 'name', 'no-name')}>"



class DatasetRelease(SpeciesEntity):
  kind = "dataset_release"
  __bucket_name = DATASET_RELEASE_BUCKET_NAME
  __blob_prefix = kind + '/${SPECIES}'


  def __repr__(self):
    return f"<{self.kind}:{getattr(self, 'name', 'no-name')}>"


  @staticmethod
  def from_name(release_name=None, species_name=None):

    # Make sure at least one argument is provided
    if release_name is None and species_name is None:
      raise ValueError('At least one of "release_name" and "species_name" must be provided.')

    # If no release name provided, use species name to look up latest release for that species
    if release_name is None:
      species = Species.from_name(species_name)
      release_name = species['release_latest']

    # Look for a release object with the matching name in the datastore
    release = DatasetRelease.get_ds(release_name)

    if release is None:
      raise NotFoundError(DatasetRelease, {'name': release_name})

    if release['species'].name != species_name:
      raise NotFoundError(DatasetRelease, {'name': release_name, 'species': species_name})

    return release


  @classmethod
  def get_props_set(cls):
    return {
      *super().get_props_set(),
      'id',
      'version',
      'wormbase_version',
      'genome',
      'report_type',
      'disabled',
      'hidden',
      'browser_tracks',      # List of browser tracks supported for this species & release, by name
    }



  @property
  def report_type(self):
    '''
      The report format for this release.
      If not set explicitly, it can also be calculated from the release version.
    '''

    # If set explicitly in object's dictionary, return that value
    if self.__dict__['report_type']:
      return ReportType.lookup(self.__dict__['report_type'])

    # If not, try to compute from version
    for report_type in DatasetRelease.all_report_types:
      if report_type.version_meets_cutoff(self.version):
        return report_type

    # If all else fails, default to None
    return None


  @report_type.setter
  def report_type(self, val):
    # Save prop in object's local dictionary
    if isinstance(val, ReportType):
      self.__dict__['report_type'] = val.name
    else:
      self.__dict__['report_type'] = val


  # Prop should default to empty list if not set
  @property
  def browser_tracks(self):
    return self.__dict__.get('browser_tracks', [])

  @browser_tracks.setter
  def browser_tracks(self, val):

    # Only allow list to be set
    if not isinstance(val, list):
      raise TypeError('Must set browser_tracks to a list.')

    # Save prop in object's local dictionary
    self.__dict__['browser_tracks'] = val




  @classmethod
  def get_bucket_name(cls):
    return cls.__bucket_name

  @classmethod
  def get_blob_prefix(cls):
    return cls.__blob_prefix

  @classmethod
  def get_path_template(cls):
    return TokenizedString(cls.get_blob_prefix() + '/${RELEASE}')

  def get_versioned_path_template(self):
    return self.get_path_template().set_tokens(RELEASE = self['version'])



  ## FASTA Filename ##

  def fasta_template_params(self):
    return {
      'SPECIES': self['species'].name,
      'RELEASE': self['version'],
      'GENOME':  self['genome'],
    }


  @staticmethod
  def get_fasta_filename_template(include_extension=True, index=False) -> TokenizedString:
    '''
      Get the FASTA file name template as a tokenized string.
      Does not include any bucket / path information; see `get_fasta_filepath_template` for the full URI.

      Arguments:
        - `include_extension` (bool): Whether to include the file extension or not.
        - `index` (bool):
              If `True`, return the name of the index file, otherwise return the name of the full FASTA file.
              Only applies if `include_extension` is `True`.
    '''
    ext = FASTA_EXTENSION_INDEX if index else FASTA_EXTENSION_FILE
    return FASTA_FILENAME_TEMPLATE + (ext if include_extension else '')


  def get_fasta_filename(self, include_extension=True, index=False):
    '''
      Get the filename for the FASTA file assocaited with this release.
      Does not include any bucket / path information; see `get_fasta_filepath_template` for the full URI.

      Arguments:
        - `include_extension` (bool): Whether to include the file extension or not.
        - `index` (bool):
            If `True`, return the name of the index file, otherwise return the name of the full FASTA file.
            Only applies if `include_extension` is `True`.
    '''
    return DatasetRelease.get_fasta_filename_template(include_extension=include_extension, index=index).get_string(**self.fasta_template_params())



  ## FASTA File Path ##

  @staticmethod
  def get_fasta_filepath_template(index=False, schema=None):
    '''
      Get a URI path for FASTA files in the datastore, as one or more tokenized strings (depends on desired schema).
    '''
    # Get the template for the filename
    filename_template = DatasetRelease.get_fasta_filename_template(include_extension=True, index=index)

    # Combine with the the dataset release bucket & path to generate a URI
    return TokenizedString.apply(
      generate_blob_uri, DatasetRelease.get_bucket_name(), DatasetRelease.get_path_template(), filename_template, schema=schema
    )


  def get_fasta_filepath(self, index=False, schema=None) -> Union[str, Tuple[str, ...]]:
    '''
      Get a URI path for the FASTA file associated with this release.
    '''
    # Get the template for the full filepath
    template = DatasetRelease.get_fasta_filepath_template(index=index, schema=schema)

    # Fill in the tokens for singleton & tuple results
    if isinstance(template, TokenizedString):
      return template.get_string(**self.fasta_template_params())
    else:
      return tuple(
        t.get_string(**self.fasta_template_params()) for t in template
      )


  def check_fasta_file_exists(self):
    '''
      Check whether this dataset release includes a FASTA file in the datastore.
    '''
    return check_blob_exists( *self.get_fasta_filepath(schema=BlobURISchema.PATH) )



  ## Report URLs ##

  def get_report_data_urls_map(self, species_name):
    '''
      Returns a dictionary of variable names for report data files mapped to their public urls in google storage
    '''
    bucket_name = self.__bucket_name
    blob_prefix = self.__blob_prefix

    tokens = {
      'RELEASE': self['version'],
      'SPECIES': species_name,
    }

    logger.debug(f'get_report_data_urls_map(bucket_name={bucket_name}, blob_prefix={blob_prefix})')

    # Check that the release has a valid report type
    if self.report_type is None:
      return None

    # Get the set of release files based on the report version
    release_files = self.report_type.get_data_map()

    # Get the set of available files for the release
    release_path = TokenizedString.replace_string(f'{blob_prefix}/$RELEASE', **tokens)
    available_files = {
      remove_prefix(file.name, release_path + '/') for file in get_blob_list(bucket_name, release_path)
    }
    available_files = {
      file for file in available_files if not file.startswith('/strain') and not file.endswith('/')
    }

    # for key, val in url_list.items:
    url_map_filtered = {}
    for key, blob_name in release_files.items():
      blob_name = TokenizedString.replace_string(blob_name, **tokens)

      if blob_name in available_files:
        url_map_filtered[key] = generate_blob_uri(bucket_name, release_path, blob_name, schema=BlobURISchema.HTTPS)
      else:
        logger.warning(f'Blob {bucket_name}/{release_path}/{blob_name} does not exist')
    
    return url_map_filtered
  

  V2 = ReportType('V2', {
    'release_notes':                     'release_notes_v2.md',
    'summary':                           'summary.md',
    'methods':                           'methods.md',
    'alignment_report':                  'alignment_report.html',
    'gatk_report':                       'gatk_report.html',
    'concordance_report':                'concordance_report.html',

    'divergent_regions_strain_bed_gz':   'browser_tracks/${RELEASE}_${SPECIES}_divergent_regions_strain.bed.gz',
    'divergent_regions_strain_bed':      'browser_tracks/${RELEASE}_${SPECIES}_divergent_regions_strain.bed',

    'soft_filter_vcf_gz':                'variation/WI.$RELEASE.soft-filter.vcf.gz',
    'soft_filter_vcf_gz_tbi':            'variation/WI.$RELEASE.soft-filter.vcf.gz.tbi',
    'soft_filter_isotype_vcf_gz':        'variation/WI.$RELEASE.soft-filter.isotype.vcf.gz',
    'soft_filter_isotype_vcf_gz_tbi':    'variation/WI.$RELEASE.soft-filter.isotype.vcf.gz.tbi',
    'hard_filter_vcf_gz':                'variation/WI.$RELEASE.hard-filter.vcf.gz',
    'hard_filter_vcf_gz_tbi':            'variation/WI.$RELEASE.hard-filter.vcf.gz.tbi',
    'hard_filter_isotype_vcf_gz':        'variation/WI.$RELEASE.hard-filter.isotype.vcf.gz',
    'hard_filter_isotype_vcf_gz_tbi':    'variation/WI.$RELEASE.hard-filter.isotype.vcf.gz.tbi',
    'impute_isotype_vcf_gz':             'variation/WI.$RELEASE.impute.isotype.vcf.gz',
    'impute_isotype_vcf_gz_tbi':         'variation/WI.$RELEASE.impute.isotype.vcf.gz.tbi',

    'hard_filter_min4_tree':             'tree/WI.$RELEASE.hard-filter.min4.tree',
    'hard_filter_min4_tree_pdf':         'tree/WI.$RELEASE.hard-filter.min4.tree.pdf',
    'hard_filter_isotype_min4_tree':     'tree/WI.$RELEASE.hard-filter.isotype.min4.tree',
    'hard_filter_isotype_min4_tree_pdf': 'tree/WI.$RELEASE.hard-filter.isotype.min4.tree.pdf',

    'haplotype_png':                     'haplotype/haplotype.png',
    'haplotype_pdf':                     'haplotype/haplotype.pdf',
    'sweep_pdf':                         'haplotype/sweep.pdf',
    'sweep_summary_tsv':                 'haplotype/sweep_summary.tsv',

    'transposon_calls':                  '${RELEASE}_${SPECIES}_transposon_calls.bed',
  }, cutoff_date=20200101)

  V1 = ReportType('V1', {
    'summary':                 'summary.md',
    'methods':                 'methods.md',

    'haplotype_png_url':       'haplotype/haplotype.png',
    'haplotype_thumb_png_url': 'haplotype/haplotype.thumb.png',
    'tajima_d_png_url':        'popgen/tajima_d.png',
    'tajima_d_thumb_png_url':  'popgen/tajima_d.thumb.png',
    'genome_svg_url':          'popgen/trees/genome.svg',

    'soft_filter_vcf_gz':      'variation/WI.$RELEASE.soft-filter.vcf.gz',
    'hard_filter_vcf_gz':      'variation/WI.$RELEASE.hard-filter.vcf.gz',
    'impute_vcf_gz':           'variation/WI.$RELEASE.impute.vcf.gz',

    'vcf_summary_url':         'multiqc_bcftools_stats.json',
    'phylo_url':               'popgen/trees/genome.pdf'
  })

  V0 = ReportType('V0', {})

  all_report_types = [V2, V1, V0]
