import os
from string import Template

from caendr.models.datastore import Entity
from caendr.services.cloud.storage import generate_blob_url, get_blob_list

V1_V2_Cutoff_Date = 20200101


class DatasetRelease(Entity):
  kind = "dataset_release"
  __bucket_name = os.environ.get('MODULE_SITE_BUCKET_PUBLIC_NAME')
  __blob_prefix = kind

  def __init__(self, version=None, wormbase_version=None, report_type=None, disabled=False, hidden=False, *args, **kwargs):
    super(DatasetRelease, self).__init__(*args, **kwargs)

    # If no version is supplied, link to empty report
    if version is None:
      self.report_type = 'V0'
      return

    # If not included, use date cutoff to identify report type
    if report_type is None:
      if int(version) < V1_V2_Cutoff_Date:
        report_type = 'V1'
      else:
        report_type = 'V2'

    self.version = str(version)
    self.wormbase_version = wormbase_version
    self.report_type = report_type
    self.disabled = disabled
    self.hidden = hidden


  def _get_public_urls(self):
    ''' Returns a list of public links for all blobs stored in the site public bucket with the dataset_release prefix '''
    blob_dir = f'{self.__blob_prefix}/{str(self.version)}'
    blob_list = get_blob_list(self.__bucket_name, blob_dir)
    public_urls = [generate_blob_url(self.__bucket_name, blob) for blob in blob_list]
    return public_urls


  def get_report_data_urls_map(self):
    ''' Returns a dictionary of variable names for report data files mapped to their public urls in google storage '''
    if self.report_type is 'V0':
      return {}
    elif self.report_type == 'V1':
      release_files = V1_Data_Map()
    elif self.report_type == 'V2':
      release_files = V2_Data_Map()
    else:
      return None

    url_list = self._get_public_urls()
    url_map_filtered = {}
    for key, name in release_files:
      blob_path = f'{self.__blob_prefix}/{name.substitute(ver=self.version)}'
      url = generate_blob_url(self.__bucket_name, blob_path)
      if url in url_list:
        url_map_filtered[key] = url

    return url_map_filtered
  

  def download_report():
    ''' Downloads report files from the dataset release on cloud storage and saves locally on app engine '''
    pass


def V2_Data_Map():
  return {
    'soft_filter_vcf_gz': Template('$ver/variation/WI.$ver.soft-filter.vcf.gz'),
    'soft_filter_vcf_gz_tbi': Template('$ver/variation/WI.$ver.soft-filter.vcf.gz.tbi'),
    'soft_filter_isotype_vcf_gz': Template('$ver/variation/WI.$ver.soft-filter.isotype.vcf.gz'),
    'soft_filter_isotype_vcf_gz_tbi': Template('$ver/variation/WI.$ver.soft-filter.isotype.vcf.gz.tbi'),
    'fhard_filter_vcf_gz': Template('$ver/variation/WI.$ver.hard-filter.vcf.gz'),
    'hard_filter_vcf_gz_tbi': Template('$ver/variation/WI.$ver.hard-filter.vcf.gz.tbi'),
    'hard_filter_isotype_vcf_gz': Template('$ver/variation/WI.$ver.hard-filter.isotype.vcf.gz'),
    'hard_filter_isotype_vcf_gz_tbi': Template('$ver/variation/WI.$ver.hard-filter.isotype.vcf.gz.tbi'),
    'impute_isotype_vcf_gz': Template('$ver/variation/WI.$ver.impute.isotype.vcf.gz'),
    'impute_isotype_vcf_gz_tbi': Template('$ver/variation/WI.$ver.impute.isotype.vcf.gz.tbi'),
    
    'hard_filter_min4_tree': Template('$ver/tree/WI.$ver.hard-filter.min4.tree'),
    'hard_filter_min4_tree_pdf': Template('$ver/tree/WI.$ver.hard-filter.min4.tree.pdf'),
    'hard_filter_isotype_min4_tree': Template('$ver/tree/WI.$ver.hard-filter.isotype.min4.tree'),
    'hard_filter_isotype_min4_tree_pdf': Template('$ver/tree/WI.$ver.hard-filter.isotype.min4.tree.pdf'),
    
    'haplotype_png': Template('$ver/haplotype/haplotype.png'),
    'haplotype_pdf': Template('$ver/haplotype/haplotype.pdf'),
    'sweep_pdf': Template('$ver/haplotype/sweep.pdf',),
    'sweep_summary_tsv': Template('$ver/haplotype/sweep_summary.tsv')
  }


def V1_Data_Map():
  return {
    'vcf_summary_url': Template('$ver/multiqc_bcftools_stats.json'),
    'phylo_url':  Template('$ver/popgen/trees/genome.pdf')
  }


def V0_Data_Map():
  return {}
  