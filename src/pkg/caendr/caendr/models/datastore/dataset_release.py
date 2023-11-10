import os
from caendr.services.logger import logger

from caendr.api.gene import remove_prefix
from caendr.models.datastore import Species, SpeciesEntity
from caendr.models.error import NotFoundError
from caendr.services.cloud.storage import BlobURISchema, generate_blob_uri, get_blob_list, check_blob_exists
from caendr.utils.tokens import TokenizedString

V1_V2_Cutoff_Date = 20200101

MODULE_SITE_BUCKET_PUBLIC_NAME = os.environ.get('MODULE_SITE_BUCKET_PUBLIC_NAME')



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
  __bucket_name = MODULE_SITE_BUCKET_PUBLIC_NAME
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

    if release['species'] != species:
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

  @staticmethod
  def get_fasta_filename_template(include_extension=True):
    return TokenizedString('${RELEASE}_${SPECIES}_${GENOME}.genome' + ('.fa' if include_extension else ''))

  def get_fasta_filename(self, include_extension=True):
    return DatasetRelease.get_fasta_filename_template(include_extension=include_extension).get_string(**{
      'SPECIES': self['species'].name,
      'RELEASE': self['version'],
      'GENOME':  self['genome'],
    })



  ## FASTA File Path ##

  # TODO: Wrap these in a utility class?
  @staticmethod
  def get_fasta_filepath_obj_template():
    return {
      'bucket': DatasetRelease.get_bucket_name(),
      'path':   DatasetRelease.get_path_template(),
      'name':   DatasetRelease.get_fasta_filename_template(include_extension=False),
      'ext':    '.fa',
    }


  def get_fasta_filepath_obj(self):

    # Construct the set of token replacements for this release's file
    params = {
      'SPECIES': self['species'].name,
      'RELEASE': self['version'],
      'GENOME':  self['genome'],
    }

    # Fill in tokens from current release in template object
    return {
      key: (val.get_string(**params) if isinstance(val, TokenizedString) else val)
        for key, val in DatasetRelease.get_fasta_filepath_obj_template().items()
    }


  def check_fasta_file_exists(self):
    obj = self.get_fasta_filepath_obj()
    return check_blob_exists(obj['bucket'], f'{ obj["path"] }/{ obj["name"] }{ obj["ext"] }')



  ## FASTA URL (full) ##

  @staticmethod
  def get_fasta_filepath_url_template():
    obj = DatasetRelease.get_fasta_filepath_obj_template()
    return TokenizedString.apply( generate_blob_uri, obj['bucket'], obj['path'], obj['name'] + obj['ext'], schema=BlobURISchema.HTTPS )

  def get_fasta_filepath_url(self):
    return DatasetRelease.get_fasta_filepath_url_template().get_string(**{
      'SPECIES': self['species'].name,
      'RELEASE': self['version'],
      'GENOME':  self['genome'],
    })



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
