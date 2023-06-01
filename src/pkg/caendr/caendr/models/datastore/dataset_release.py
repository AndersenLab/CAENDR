import os
from string import Template
from caendr.services.logger import logger

from caendr.models.datastore import Entity
from caendr.services.cloud.storage import generate_blob_url, get_blob, check_blob_exists
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



class DatasetRelease(Entity):
  kind = "dataset_release"
  __bucket_name = MODULE_SITE_BUCKET_PUBLIC_NAME
  __blob_prefix = kind + '/c_${SPECIES}'


  def __repr__(self):
    return f"<{self.kind}:{getattr(self, 'name', 'no-name')}>"


  @classmethod
  def get_props_set(cls):
    return {
      *super().get_props_set(),
      'id',
      'version',
      'wormbase_version',
      'report_type',
      'disabled',
      'hidden',
      'species',
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



  def get_report_data_urls_map(self, species_name):
    '''
      Returns a dictionary of variable names for report data files mapped to their public urls in google storage
    '''
    bucket_name = self.__bucket_name
    blob_prefix = self.__blob_prefix

    logger.debug(f'get_report_data_urls_map(bucket_name={bucket_name}, blob_prefix={blob_prefix})')

    # Check that the release has a valid report type
    if self.report_type is None:
      return None

    # Get the set of release files based on the report version
    release_files = self.report_type.get_data_map()

    # for key, val in url_list.items:
    url_map_filtered = {}
    for key, blob_name in release_files.items():
      blob_path = TokenizedString(f'{blob_prefix}/{blob_name}').get_string(**{
        'RELEASE': self['version'],
        'SPECIES': species_name,
      })

      if check_blob_exists(bucket_name, blob_path):
        url_map_filtered[key] = generate_blob_url(bucket_name, blob_path)
      else:
        logger.warning(f'Blob {blob_path} does not exist')
    
    return url_map_filtered
  

  V2 = ReportType('V2', {
    'release_notes':                     '$RELEASE/release_notes.md',
    'summary':                           '$RELEASE/summary.md',
    'methods':                           '$RELEASE/methods.md',
    'alignment_report':                  '$RELEASE/alignment_report.html',
    'gatk_report':                       '$RELEASE/gatk_report.html',
    'concordance_report':                '$RELEASE/concordance_report.html',

    'divergent_regions_strain_bed_gz':   '$RELEASE/divergent_regions_strain.$RELEASE.bed.gz',
    'divergent_regions_strain_bed':      '$RELEASE/divergent_regions_strain.$RELEASE.bed',

    'soft_filter_vcf_gz':                '$RELEASE/variation/WI.$RELEASE.soft-filter.vcf.gz',
    'soft_filter_vcf_gz_tbi':            '$RELEASE/variation/WI.$RELEASE.soft-filter.vcf.gz.tbi',
    'soft_filter_isotype_vcf_gz':        '$RELEASE/variation/WI.$RELEASE.soft-filter.isotype.vcf.gz',
    'soft_filter_isotype_vcf_gz_tbi':    '$RELEASE/variation/WI.$RELEASE.soft-filter.isotype.vcf.gz.tbi',
    'hard_filter_vcf_gz':                '$RELEASE/variation/WI.$RELEASE.hard-filter.vcf.gz',
    'hard_filter_vcf_gz_tbi':            '$RELEASE/variation/WI.$RELEASE.hard-filter.vcf.gz.tbi',
    'hard_filter_isotype_vcf_gz':        '$RELEASE/variation/WI.$RELEASE.hard-filter.isotype.vcf.gz',
    'hard_filter_isotype_vcf_gz_tbi':    '$RELEASE/variation/WI.$RELEASE.hard-filter.isotype.vcf.gz.tbi',
    'impute_isotype_vcf_gz':             '$RELEASE/variation/WI.$RELEASE.impute.isotype.vcf.gz',
    'impute_isotype_vcf_gz_tbi':         '$RELEASE/variation/WI.$RELEASE.impute.isotype.vcf.gz.tbi',

    'hard_filter_min4_tree':             '$RELEASE/tree/WI.$RELEASE.hard-filter.min4.tree',
    'hard_filter_min4_tree_pdf':         '$RELEASE/tree/WI.$RELEASE.hard-filter.min4.tree.pdf',
    'hard_filter_isotype_min4_tree':     '$RELEASE/tree/WI.$RELEASE.hard-filter.isotype.min4.tree',
    'hard_filter_isotype_min4_tree_pdf': '$RELEASE/tree/WI.$RELEASE.hard-filter.isotype.min4.tree.pdf',

    'haplotype_png':                     '$RELEASE/haplotype/haplotype.png',
    'haplotype_pdf':                     '$RELEASE/haplotype/haplotype.pdf',
    'sweep_pdf':                         '$RELEASE/haplotype/sweep.pdf',
    'sweep_summary_tsv':                 '$RELEASE/haplotype/sweep_summary.tsv'
  }, cutoff_date=20200101)

  V1 = ReportType('V1', {
    'summary':                 '$RELEASE/summary.md',
    'methods':                 '$RELEASE/methods.md',

    'haplotype_png_url':       '$RELEASE/haplotype/haplotype.png',
    'haplotype_thumb_png_url': '$RELEASE/haplotype/haplotype.thumb.png',
    'tajima_d_png_url':        '$RELEASE/popgen/tajima_d.png',
    'tajima_d_thumb_png_url':  '$RELEASE/popgen/tajima_d.thumb.png',
    'genome_svg_url':          '$RELEASE/popgen/trees/genome.svg',

    'soft_filter_vcf_gz':      '$RELEASE/variation/WI.$RELEASE.soft-filter.vcf.gz',
    'hard_filter_vcf_gz':      '$RELEASE/variation/WI.$RELEASE.hard-filter.vcf.gz',
    'impute_vcf_gz':           '$RELEASE/variation/WI.$RELEASE.impute.vcf.gz',

    'vcf_summary_url':         '$RELEASE/multiqc_bcftools_stats.json',
    'phylo_url':               '$RELEASE/popgen/trees/genome.pdf'
  })

  V0 = ReportType('V0', {})

  all_report_types = [V2, V1, V0]
