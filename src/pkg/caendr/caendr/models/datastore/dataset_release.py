import os
from string import Template
from logzero import logger

from caendr.models.datastore import Entity
from caendr.services.cloud.storage import generate_blob_url, get_blob, check_blob_exists

V1_V2_Cutoff_Date = 20200101

MODULE_SITE_BUCKET_PUBLIC_NAME = os.environ.get('MODULE_SITE_BUCKET_PUBLIC_NAME')

class DatasetRelease(Entity):
  kind = "dataset_release"
  __bucket_name = MODULE_SITE_BUCKET_PUBLIC_NAME
  __blob_prefix = f'{kind}/c_elegans'

  def __init__(self, *args, **kwargs):
    super(DatasetRelease, self).__init__(*args, **kwargs)
  
  def set_properties(self, **kwargs):
    props = self.get_props_set()
    self.__dict__.update((k, v) for k, v in kwargs.items() if k in props)
    
    if not self.report_type and int(self.version) > 0:
      if int(self.version) < V1_V2_Cutoff_Date:
        self.report_type = 'V1'
      else:
        self.report_type = 'V2'

  @classmethod
  def get_props_set(cls):
    return {'id',
            'version', 
            'wormbase_version',
            'report_type',
            'disabled',
            'hidden'}
    
  @classmethod
  def get_bucket_name(cls):
    return cls.__bucket_name
  
  @classmethod
  def get_blob_prefix(cls):
    return cls.__blob_prefix


  def get_report_data_urls_map(self):
    ''' Returns a dictionary of variable names for report data files mapped to their public urls in google storage '''
    bucket_name=self.__bucket_name
    blob_prefix=self.__blob_prefix
    
    logger.debug(f'get_report_data_urls_map(bucket_name={bucket_name}, blob_prefix={blob_prefix})')
    
    if self.report_type == 'V0':
      return {}
    elif self.report_type == 'V1':
      release_files = V1_Data_Map()
    elif self.report_type == 'V2':
      release_files = V2_Data_Map()
    else:
      return None

    # for key, val in url_list.items:
    url_map_filtered = {}
    for key, val in release_files.items():
      t = Template(val)
      blob_name = t.substitute(ver=self.version)
      blob_path = f'{blob_prefix}/{blob_name}'
      if check_blob_exists(bucket_name, blob_path):
        url_map_filtered[key] = generate_blob_url(bucket_name, blob_path)
      else:
        logger.warning(f'Blob {blob_path} does not exist')
    
    return url_map_filtered
  

def V2_Data_Map():
  return {
    'release_notes': '$ver/release_notes.md',
    'summary': '$ver/summary.md',
    'methods': '$ver/methods.md',
    'alignment_report': '$ver/alignment_report.html',
    'gatk_report': '$ver/gatk_report.html',
    'concordance_report': '$ver/concordance_report.html',
    
    'divergent_regions_strain_bed_gz': '$ver/divergent_regions_strain.$ver.bed.gz',
    'divergent_regions_strain_bed': '$ver/divergent_regions_strain.$ver.bed',

    'soft_filter_vcf_gz': '$ver/variation/WI.$ver.soft-filter.vcf.gz',
    'soft_filter_vcf_gz_tbi': '$ver/variation/WI.$ver.soft-filter.vcf.gz.tbi',
    'soft_filter_isotype_vcf_gz': '$ver/variation/WI.$ver.soft-filter.isotype.vcf.gz',
    'soft_filter_isotype_vcf_gz_tbi': '$ver/variation/WI.$ver.soft-filter.isotype.vcf.gz.tbi',
    'hard_filter_vcf_gz': '$ver/variation/WI.$ver.hard-filter.vcf.gz',
    'hard_filter_vcf_gz_tbi': '$ver/variation/WI.$ver.hard-filter.vcf.gz.tbi',
    'hard_filter_isotype_vcf_gz': '$ver/variation/WI.$ver.hard-filter.isotype.vcf.gz',
    'hard_filter_isotype_vcf_gz_tbi': '$ver/variation/WI.$ver.hard-filter.isotype.vcf.gz.tbi',
    'impute_isotype_vcf_gz': '$ver/variation/WI.$ver.impute.isotype.vcf.gz',
    'impute_isotype_vcf_gz_tbi': '$ver/variation/WI.$ver.impute.isotype.vcf.gz.tbi',
    
    'hard_filter_min4_tree': '$ver/tree/WI.$ver.hard-filter.min4.tree',
    'hard_filter_min4_tree_pdf': '$ver/tree/WI.$ver.hard-filter.min4.tree.pdf',
    'hard_filter_isotype_min4_tree': '$ver/tree/WI.$ver.hard-filter.isotype.min4.tree',
    'hard_filter_isotype_min4_tree_pdf': '$ver/tree/WI.$ver.hard-filter.isotype.min4.tree.pdf',
    
    'haplotype_png': '$ver/haplotype/haplotype.png',
    'haplotype_pdf': '$ver/haplotype/haplotype.pdf',
    'sweep_pdf': '$ver/haplotype/sweep.pdf',
    'sweep_summary_tsv': '$ver/haplotype/sweep_summary.tsv'
  }


def V1_Data_Map():
  return {
    'summary': '$ver/summary.md',
    'methods': '$ver/methods.md',
    'haplotype_png_url': '$ver/haplotype/haplotype.png',
    'haplotype_thumb_png_url': '$ver/haplotype/haplotype.thumb.png',
    'tajima_d_png_url': '$ver/popgen/tajima_d.png',
    'tajima_d_thumb_png_url': '$ver/popgen/tajima_d.thumb.png',
    'genome_svg_url': '$ver/popgen/trees/genome.svg',
    
    'soft_filter_vcf_gz': '$ver/variation/WI.$ver.soft-filter.vcf.gz',
    'hard_filter_vcf_gz': '$ver/variation/WI.$ver.hard-filter.vcf.gz',
    'impute_vcf_gz': '$ver/variation/WI.$ver.impute.vcf.gz',

    
    'vcf_summary_url': '$ver/multiqc_bcftools_stats.json',
    'phylo_url': '$ver/popgen/trees/genome.pdf'
    
  }


def V0_Data_Map():
  return {}
  