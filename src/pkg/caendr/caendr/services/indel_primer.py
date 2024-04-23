import tabix
from cyvcf2 import VCF
from caendr.services.logger import logger

from caendr.models.datastore import IndelPrimerReport, Species

from caendr.services.cloud.storage import (
    BlobURISchema,
    download_blob_to_file,
    generate_blob_uri,
)

from caendr.utils.constants import CHROM_NUMERIC
from caendr.utils.env import get_env_var



MODULE_SITE_BUCKET_PRIVATE_NAME = get_env_var('MODULE_SITE_BUCKET_PRIVATE_NAME')
INDEL_PRIMER_CONTAINER_NAME     = get_env_var('INDEL_PRIMER_CONTAINER_NAME', can_be_none=True)
INDEL_PRIMER_TOOL_PATH          = get_env_var('INDEL_PRIMER_TOOL_PATH')



# =========================== #
#    pairwise_indel_finder    #
# =========================== #

MIN_SV_SIZE = 50
MAX_SV_SIZE = 500

SV_COLUMNS = [
    "CHROM",
    "START",
    "END",
    "SVTYPE",
    "STRAIN",
    "GT",
    "SIZE",
]

CHROMOSOME_CHOICES = [(x, x) for x in CHROM_NUMERIC.keys()]
COLUMNS = ["CHROM", "START", "STOP", "?", "TYPE", "STRAND", ""]



def get_bed_url(species, release = None, secure = True):
  release = release or Species.from_name(species).release_pif
  filename = IndelPrimerReport.get_source_filename(species, release)
  return generate_blob_uri(
    MODULE_SITE_BUCKET_PRIVATE_NAME, INDEL_PRIMER_TOOL_PATH, f'{filename}.bed.gz', schema = BlobURISchema.http(secure=secure)
  )

def get_vcf_url(species, release = None, secure = True):
  release = release or Species.from_name(species).release_pif
  filename = IndelPrimerReport.get_source_filename(species, release)
  return generate_blob_uri(
    MODULE_SITE_BUCKET_PRIVATE_NAME, INDEL_PRIMER_TOOL_PATH, f'{filename}.vcf.gz', schema = BlobURISchema.http(secure=secure)
  )


def download_vcf_index_file(species, release = None):
  '''
    Download the VCF index file for the indel primer tool, keeping the same name used in datastore.
  '''
  filename = IndelPrimerReport.get_source_filename(species, release) + '.vcf.gz.csi'
  download_blob_to_file(MODULE_SITE_BUCKET_PRIVATE_NAME, INDEL_PRIMER_TOOL_PATH, filename)


def get_sv_strains(species, release = None):
  logger.debug('get_sv_strains')

  # Use the given release if provided, otherwise default to species value
  release = release or Species.from_name(species).release_pif

  # Compute and log the URL of the VCF file on GCP
  vcf_url = get_vcf_url( species, release, secure=False )
  logger.debug(f'get_sv_strains: reading strains from {vcf_url}')

  # Explicitly download the index file
  # IMPORTANT: This solves a memory allocation error in the cyvcf library
  download_vcf_index_file(species, release)

  # Read the list of strains from the vcf file
  try:
    return VCF( vcf_url ).samples
  except Exception as ex:
    logger.error(f'Error reading VCF file "{vcf_url}": {ex}')
    raise


def get_indel_primer_chrom_choices(): 
  return CHROMOSOME_CHOICES
  
  
def get_indel_primer_strain_choices(species, release = None):
  return [ (x, x) for x in get_sv_strains(species, release) ]


def overlaps(s1, e1, s2, e2):
  return s1 <= s2 <= e1 or s2 <= s1 <= e2


def query_indels_and_mark_overlaps(species, strain_1, strain_2, chromosome, start, stop):
  results = []
  strain_cmp = [ strain_1, strain_2 ]

  tb = tabix.open( get_bed_url(species, secure=False) )
  query = tb.query(chromosome, start, stop)

  for row in query:
    row = dict(zip(SV_COLUMNS, row))
    row["START"] = int(row["START"])
    row["END"]   = int(row["END"])

    if row["STRAIN"] in strain_cmp and ( MIN_SV_SIZE <= int(row["SIZE"]) <= MAX_SV_SIZE ):
      row["site"] = f"{row['CHROM']}:{row['START']}-{row['END']} ({row['SVTYPE']})"
      results.append(row)
  
  # mark overlaps
  if results:
    results[0]['overlap'] = False
    first = results[0]
    for idx, row in enumerate(results[1:]):
      row["overlap"] = overlaps(first["START"], first["END"], row["START"], row["END"])
      if row["overlap"]:
        results[idx]['overlap'] = True
      first = row
    
    # Filter overlaps
    results = [x for x in results if x['overlap'] is False]
    return sorted(results, key=lambda x: (x["START"], x["END"]))
  return []
