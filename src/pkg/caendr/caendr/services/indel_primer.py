import tabix
import os
import io
import json
import numpy as np
import pandas as pd

from cyvcf2 import VCF
from caendr.services.logger import logger

from caendr.models.datastore import IndelPrimer, SPECIES_LIST
from caendr.models.error     import CachedDataError, DuplicateDataError, NotFoundError, EmptyReportDataError, EmptyReportResultsError, UnfinishedReportError

from caendr.services.cloud.storage import get_blob, generate_blob_url
from caendr.services.tools import submit_job

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
  return IndelPrimer.get_ds(id)


def get_all_indel_primers():
  logger.debug(f'Getting all indel primers...')
  primers = IndelPrimer.query_ds()
  return IndelPrimer.sort_by_created_date(primers, reverse=True)


def get_user_indel_primers(username):
  logger.debug(f'Getting all indel primers for user: username:{username}')
  filters = [('username', '=', username)]
  primers = IndelPrimer.query_ds(filters=filters)
  return IndelPrimer.sort_by_created_date(primers, reverse=True)


def get_bed_url(species, release = None, secure = True):
  release = release or SPECIES_LIST[species].indel_primer_ver
  filename = IndelPrimer.get_source_filename(species, release)
  return generate_blob_url(
    MODULE_SITE_BUCKET_PRIVATE_NAME, f"{INDEL_PRIMER_TOOL_PATH}/{filename}.bed.gz", secure = secure
  )

def get_vcf_url(species, release = None, secure = True):
  release = release or SPECIES_LIST[species].indel_primer_ver
  filename = IndelPrimer.get_source_filename(species, release)
  return generate_blob_url(
    MODULE_SITE_BUCKET_PRIVATE_NAME, f"{INDEL_PRIMER_TOOL_PATH}/{filename}.vcf.gz", secure = secure
  )


def get_sv_strains(species, release = None):
  release = release or SPECIES_LIST[species].indel_primer_ver
  return VCF( get_vcf_url( species, release, secure=False ) ).samples


def get_indel_primer_chrom_choices(): 
  return CHROMOSOME_CHOICES
  
  
def get_indel_primer_strain_choices(species, release = None):
  return [ (x, x) for x in get_sv_strains(species, release) ]


def overlaps(s1, e1, s2, e2):
  return s1 <= s2 <= e1 or s2 <= s1 <= e2


def fetch_ip_data(ip: IndelPrimer):
  return get_blob(ip.get_bucket_name(), ip.get_data_blob_path())


def fetch_ip_result(ip: IndelPrimer):
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


def create_new_indel_primer(user, data, no_cache=False):
  try:
    return submit_job(IndelPrimer, user, data, no_cache=no_cache)

  except DuplicateDataError as ex:
    print('Duplicate data found!')
    return ex.args[0]

  except CachedDataError as ex:
    print('Cached results found!')
    return ex.args[0]



def update_indel_primer_status(id: str, status: str=None, operation_name: str=None):
  logger.debug(f'update_indel_primer_status: id:{id} status:{status} operation_name:{operation_name}')

  m = IndelPrimer.get_ds(id)
  if m is None:
    raise NotFoundError(f'No Indel Primer with ID "{id}" was found.')

  if status:
    m.set_properties(status=status)
  if operation_name:
    m.set_properties(operation_name=operation_name)

  m.save()
  return m



def fetch_indel_primer_report(report):

  # Fetch job data (parameters of original query) and results
  data   = fetch_ip_data(report)
  result = fetch_ip_result(report)

  # If no indel primer submission exists, return 404
  if data is None:
    raise EmptyReportDataError(report.id)

  # Parse submission data into JSON object
  data = json.loads(data.download_as_string().decode('utf-8'))
  # logger.debug(data)

  # If no result file exists yet, just expose the parsed data file
  if result is None:
    raise UnfinishedReportError(report.id, data=data)

  # Download results file as string
  result = result.download_as_string().decode('utf-8')

  # Check for empty results file
  if len(result) == 0:
    raise EmptyReportResultsError(report.id)

  # Separate results by tabs, and check for empty data frame (headers exist but no data)
  result = pd.read_csv(io.StringIO(result), sep="\t")

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
