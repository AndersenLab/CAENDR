import tabix
import os
import io
import numpy as np

from cyvcf2 import VCF
from caendr.services.logger import logger

from caendr.models.datastore import IndelPrimerReport, Species
from caendr.models.error     import EmptyReportDataError, EmptyReportResultsError

from caendr.services.cloud.storage import (
    download_blob_as_dataframe,
    download_blob_as_json,
    download_blob_to_file,
    generate_blob_url,
    get_blob,
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

def get_indel_primer(id):
  '''
    Get the Indel Primer with the given ID.
    If no such submission exists, returns None.
  '''
  return IndelPrimerReport.get_ds(id)


def get_indel_primers(username=None, filter_errs=False):
  '''
    Get a list of Indel Finder reports, sorted by most recent.

    Args:
      username (str | None):
        If provided, only return reports owned by the given user.
      filter_errs (bool):
        If True, skips all entities that throw an error when initializing.
        If False, populates as many fields of those entities as possible.
  '''
  # Filter by username if provided, and log event accordingly
  if username:
    logger.debug(f'Getting all indel primers for user: username:{username}')
    filters = [('username', '=', username)]
  else:
    logger.debug(f'Getting all indel primers...')
    filters = []

  # Get list of reports and filter by date
  primers = IndelPrimerReport.query_ds(safe=not filter_errs, ignore_errs=filter_errs, filters=filters)
  return IndelPrimerReport.sort_by_created_date(primers, reverse=True)


def get_bed_url(species, release = None, secure = True):
  release = release or Species.from_name(species).release_pif
  filename = IndelPrimerReport.get_source_filename(species, release)
  return generate_blob_url(
    MODULE_SITE_BUCKET_PRIVATE_NAME, f"{INDEL_PRIMER_TOOL_PATH}/{filename}.bed.gz", secure = secure
  )

def get_vcf_url(species, release = None, secure = True):
  release = release or Species.from_name(species).release_pif
  filename = IndelPrimerReport.get_source_filename(species, release)
  return generate_blob_url(
    MODULE_SITE_BUCKET_PRIVATE_NAME, f"{INDEL_PRIMER_TOOL_PATH}/{filename}.vcf.gz", secure = secure
  )


def download_vcf_index_file(species, release = None):
  filename = IndelPrimerReport.get_source_filename(species, release) + '.vcf.gz.csi'
  download_blob_to_file(MODULE_SITE_BUCKET_PRIVATE_NAME, f"{INDEL_PRIMER_TOOL_PATH}/{filename}", filename)


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


def fetch_ip_data(ip: IndelPrimerReport):
  return get_blob(ip.get_bucket_name(), ip.get_data_blob_path())


def fetch_ip_result(ip: IndelPrimerReport):
  return get_blob(ip.get_bucket_name(), ip.get_result_blob_path())


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



def fetch_indel_primer_report(report):

  # Fetch job data (parameters of original query) and results
  data   = fetch_ip_data(report)
  result = fetch_ip_result(report)

  # If no indel primer submission exists, return 404
  if data is None:
    raise EmptyReportDataError(report.id)

  # Parse submission data into JSON object
  data = download_blob_as_json(data)

  # If result file exists, download & parse it into a dataframe
  if result is not None:
    result = download_blob_as_dataframe(result)

    # Check for empty results file
    if result is None:
      raise EmptyReportResultsError(report.id)

  # Return the data & results as Python objects
  return data, result



def modify_indel_primer_result(result):

  # If no results, return as None
  if result is None or result.empty:
    return None, None

  # Left primer
  result['left_primer_start'] = result.amplicon_region.apply(lambda x: x.split(":")[1].split("-")[0]).astype(int)
  result['left_primer_stop']  = result.apply(lambda x: len(x['primer_left']) + x['left_primer_start'], axis=1)

  # Right primer
  result['right_primer_stop']  = result.amplicon_region.apply(lambda x: x.split(":")[1].split("-")[1]).astype(int)
  result['right_primer_start'] = result.apply(lambda x:  x['right_primer_stop'] - len(x['primer_right']), axis=1)

  # Output left and right melting temperatures.
  result[["left_melting_temp", "right_melting_temp"]] = result["melting_temperature"].str.split(",", expand = True)

  # REF Strain and ALT Strain
  ref_strain = result['0/0'].unique()[0]
  alt_strain = result['1/1'].unique()[0]

  # Extract chromosome and amplicon start/stop
  result[[None, "amp_start", "amp_stop"]] = result.amplicon_region.str.split(pat=":|-", expand=True)

  # Convert types
  result.amp_start = result.amp_start.astype(int)
  result.amp_stop  = result.amp_stop.astype(int)

  result["N"] = np.arange(len(result)) + 1

  # Associate table column names with the corresponding fields in the result objects
  columns = [

    # Basic Info
    ("Primer Set", "N"),
    ("Chrom", "CHROM"),

    # Left Primer
    ("Left Primer (LP)", "primer_left"),
    ("LP Start",         "left_primer_start"),
    ("LP Stop",          "left_primer_stop"),
    ("LP Melting Temp",  "left_melting_temp"),

    # Right Primer
    ("Right Primer (RP)", "primer_right"),
    ("RP Start",          "right_primer_start"),
    ("RP Stop",           "right_primer_stop"),
    ("RP Melting Temp",   "right_melting_temp"),

    # Amplicon
    (f"{ref_strain} (REF) amplicon size", "REF_product_size"),
    (f"{alt_strain} (ALT) amplicon size", "ALT_product_size"),
  ]

  # Convert list of (name, field) tuples to list of names and list of fields
  column_names, column_fields = zip(*columns)

  # Create table from results & columns
  format_table = result[list(column_fields)]
  format_table.columns = column_names

  return result, format_table
