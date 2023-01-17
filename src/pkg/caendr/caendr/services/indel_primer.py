import tabix
import os
import json

from cyvcf2 import VCF
from logzero import logger

from caendr.models.error import EnvVarError
from caendr.models.datastore import IndelPrimer
from caendr.models.task import IndelPrimerTask

from caendr.services.cloud.storage import upload_blob_from_string, get_blob, check_blob_exists
from caendr.services.tool_versions import get_current_container_version

from caendr.utils.constants import CHROM_NUMERIC
from caendr.utils.data import unique_id



MODULE_SITE_BUCKET_PRIVATE_NAME   = os.environ.get('MODULE_SITE_BUCKET_PRIVATE_NAME')
INDEL_PRIMER_CONTAINER_NAME       = os.environ.get('INDEL_PRIMER_CONTAINER_NAME')

SV_BED_FILENAME = os.environ.get('INDEL_PRIMER_SV_BED_FILENAME')
SV_VCF_FILENAME = os.environ.get('INDEL_PRIMER_SV_VCF_FILENAME')

if not SV_BED_FILENAME:
  logger.debug("No value provided for INDEL_PRIMER_SV_BED_FILENAME")
  raise EnvVarError()

if not SV_VCF_FILENAME:
  logger.debug("No value provided for INDEL_PRIMER_SV_VCF_FILENAME")
  raise EnvVarError()



# =========================== #
#    pairwise_indel_finder    #
# =========================== #

MIN_SV_SIZE = 50
MAX_SV_SIZE = 500

# Initial load of strain list from sv_data
# This is run when the server is started.
# NOTE: Tabix cannot make requests over https!
SV_BED_URL = f"http://storage.googleapis.com/{MODULE_SITE_BUCKET_PRIVATE_NAME}/tools/pairwise_indel_primer/{SV_BED_FILENAME}"
SV_VCF_URL = f"http://storage.googleapis.com/{MODULE_SITE_BUCKET_PRIVATE_NAME}/tools/pairwise_indel_primer/{SV_VCF_FILENAME}"

SV_STRAINS = VCF(SV_VCF_URL).samples
SV_COLUMNS = [
    "CHROM",
    "START",
    "END",
    "SVTYPE",
    "STRAIN",
    "GT",
    "SIZE",
]

STRAIN_CHOICES = [(x, x) for x in SV_STRAINS]
CHROMOSOME_CHOICES = [(x, x) for x in CHROM_NUMERIC.keys()]
COLUMNS = ["CHROM", "START", "STOP", "?", "TYPE", "STRAND", ""]

def get_indel_primer(id):
  return IndelPrimer(id)


def get_sv_strains():
  return SV_STRAINS


def get_all_indel_primers():
  logger.debug(f'Getting all indel primers...')
  primers = IndelPrimer.query_ds()
  return IndelPrimer.sort_by_created_date(primers, reverse=True)


def get_user_indel_primers(username):
  logger.debug(f'Getting all indel primers for user: username:{username}')
  filters = [('username', '=', username)]
  primers = IndelPrimer.query_ds(filters=filters)
  return IndelPrimer.sort_by_created_date(primers, reverse=True)


def get_indel_primer_chrom_choices(): 
  return CHROMOSOME_CHOICES
  
  
def get_indel_primer_strain_choices():
  return STRAIN_CHOICES


def overlaps(s1, e1, s2, e2):
  return s1 <= s2 <= e1 or s2 <= s1 <= e2
  

def fetch_ip_data(ip: IndelPrimer):
  return get_blob(ip.get_bucket_name(), ip.get_data_blob_path())


def fetch_ip_result(ip: IndelPrimer):
  return get_blob(ip.get_bucket_name(), ip.get_result_blob_path())


def query_indels_and_mark_overlaps(strain_1, strain_2, chromosome, start, stop):
  results = []
  strain_cmp = [ strain_1, strain_2 ]

  tb = tabix.open(SV_BED_URL)
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


def create_new_indel_primer(username, site, strain_1, strain_2, size, data_hash, no_cache=False):
  logger.debug(f'''Creating new Indel Primer:
    username:  "{username}"
    site:      {site}
    strain_1:  {strain_1}
    strain_2:  {strain_2}
    size:      {size}
    data_hash: {data_hash}
    cache:     {not no_cache}''')

  # Load container version info
  c = get_current_container_version(INDEL_PRIMER_CONTAINER_NAME)

  # Check for existing indel primer matching data_hash & user
  if not no_cache:
    ips = IndelPrimer.query_ds(filters=[('data_hash', '=', data_hash)])
    if ips[0]:
      if ips[0].username == username and ips[0].container_equals(c):
        return ips[0]

  # Compute unique ID for new Indel Primer entity
  id = unique_id()

  # Create Indel Primer entity & upload to GCP
  ip = IndelPrimer(id, **{
    'id':                id,
    'data_hash':         data_hash,
    'username':          username,
    'status':            'SUBMITTED',
    'site':              site,
    'strain_1':          strain_1,
    'strain_2':          strain_2,
    'size':              size,
    'container_repo':    c.repo,
    'container_name':    c.container_name,
    'container_version': c.container_tag,
    'sv_bed_filename':   SV_BED_FILENAME,
    'sv_vcf_filename':   SV_VCF_FILENAME,
  })
  ip.save()

  # Check if there is already a result
  if not no_cache:
    if check_blob_exists(ip.get_bucket_name(), ip.get_result_blob_path()):
      ip.status = 'COMPLETE'
      ip.save()
      return ip

  # Collect data about this run
  data = {
    'site': site,
    'strain_1': strain_1,
    'strain_2': strain_2,
    'size': size
  }

  # Upload data.tsv to google storage
  bucket = ip.get_bucket_name()
  blob = ip.get_data_blob_path()
  upload_blob_from_string(bucket, json.dumps(data), blob)

  # Schedule mapping in task queue
  task = _create_indel_primer_task(ip)
  result = task.submit()

  # Update entity status to reflect whether task was submitted successfully
  ip.status = 'SUBMITTED' if result else 'ERROR'
  ip.save()

  # Return resulting Indel Primer entity
  return ip


def _create_indel_primer_task(ip):
  """
    Convert an Indel Primer object to an Indel Primer task.
  """
  return IndelPrimerTask(**{
    'id':                ip.id,
    'kind':              IndelPrimer.kind,
    'data_hash':         ip.data_hash,
    'username':          ip.username,
    'site':              ip.site,
    'strain_1':          ip.strain_1,
    'strain_2':          ip.strain_2,
    'container_repo':    ip.container_repo,
    'container_name':    ip.container_name,
    'container_version': ip.container_version,
    'sv_bed_filename':   ip.sv_bed_filename,
    'sv_vcf_filename':   ip.sv_vcf_filename,
  })


def update_indel_primer_status(id: str, status: str=None, operation_name: str=None):
  logger.debug(f'update_indel_primer_status: id:{id} status:{status} operation_name:{operation_name}')
  m = IndelPrimer(id)
  if status:
    m.set_properties(status=status)
  if operation_name:
    m.set_properties(operation_name=operation_name)
    
  m.save()
  return m