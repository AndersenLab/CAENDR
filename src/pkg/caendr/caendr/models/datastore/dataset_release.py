import os
from string import Template
from logzero import logger

from caendr.models.datastore import Entity
from caendr.services.cloud.storage import generate_blob_url, get_blob_list

V1_V2_Cutoff_Date = 20200101


class DatasetRelease(Entity):
  kind = "dataset_release"
  __bucket_name = os.environ.get('MODULE_SITE_BUCKET_PUBLIC_NAME')
  __blob_prefix = kind

  def __init__(self, *args, **kwargs):
    super(DatasetRelease, self).__init__(*args, **kwargs)
   
  def set_properties(self, **kwargs):
    self.version = kwargs.get('version')
    self.wormbase_version = kwargs.get('wormbase_version')
    self.report_type = kwargs.get('report_type')
    self.disabled = kwargs.get('disabled')
    self.hidden = kwargs.get('hidden')
    
    if not self.report_type and int(self.version) > 0:
      if int(self.version) < V1_V2_Cutoff_Date:
        self.report_type = 'V1'
      else:
        self.report_type = 'V2'


  @classmethod
  def get_bucket_name(cls):
    return cls.__bucket_name
  
  @classmethod
  def get_blob_prefix(cls):
    return cls.__blob_prefix

  def _get_public_urls(self, bucket_name=None, blob_prefix=None):
    ''' Returns a list of public links for all blobs stored in the site public bucket with the dataset_release prefix '''
    if not bucket_name:
      bucket_name=self.__bucket_name
    if not blob_prefix:
      blob_prefix=self.__blob_prefix
    
    blob_dir = f'{blob_prefix}/{str(self.version)}'
    blob_list = get_blob_list(bucket_name, blob_dir)
    public_urls = [generate_blob_url(blob.bucket.name, blob.name) for blob in blob_list]
    return public_urls

  def get_report_data_urls_map(self, bucket_name=None, blob_prefix=None):
    ''' Returns a dictionary of variable names for report data files mapped to their public urls in google storage '''
    if not bucket_name:
      bucket_name=self.__bucket_name
    if not blob_prefix:
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

    url_list = self._get_public_urls(bucket_name=bucket_name, blob_prefix=blob_prefix)
    url_map_filtered = {}
    for key, val in release_files.items():
      t = Template(val)
      blob_name = t.substitute(ver=self.version)
      blob_path = f'{blob_prefix}/{blob_name}'
      url = generate_blob_url(bucket_name, blob_path)
      if url in url_list:
        url_map_filtered[key] = url

    return url_map_filtered
  

def V2_Data_Map():
  return {
    'soft_filter_vcf_gz': '$ver/variation/WI.$ver.soft-filter.vcf.gz',
    'soft_filter_vcf_gz_tbi': '$ver/variation/WI.$ver.soft-filter.vcf.gz.tbi',
    'soft_filter_isotype_vcf_gz': '$ver/variation/WI.$ver.soft-filter.isotype.vcf.gz',
    'soft_filter_isotype_vcf_gz_tbi': '$ver/variation/WI.$ver.soft-filter.isotype.vcf.gz.tbi',
    'fhard_filter_vcf_gz': '$ver/variation/WI.$ver.hard-filter.vcf.gz',
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
    'vcf_summary_url': '$ver/multiqc_bcftools_stats.json',
    'phylo_url': '$ver/popgen/trees/genome.pdf'
  }


def V0_Data_Map():
  return {}
  