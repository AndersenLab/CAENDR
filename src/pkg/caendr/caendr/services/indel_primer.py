import tabix
import os
import json

from cyvcf2 import VCF
from logzero import logger

from caendr.models.datastore import IndelPrimer
from caendr.models.task import IndelPrimerTask

from caendr.services.cloud.secret import get_secret
from caendr.services.cloud.datastore import query_ds_entities
from caendr.services.cloud.task import add_task
from caendr.services.cloud.storage import upload_blob_from_string, get_blob, check_blob_exists
from caendr.services.tool_versions import get_current_container_version

from caendr.utils.constants import CHROM_NUMERIC
from caendr.utils.data import unique_id

# TODO: remove this static value
MODULE_SITE_BUCKET_PRIVATE_NAME = 'elegansvariation.org'
# MODULE_SITE_BUCKET_PRIVATE_NAME = os.environ.get('MODULE_SITE_BUCKET_PRIVATE_NAME')
INDEL_PRIMER_CONTAINER_NAME = os.environ.get('INDEL_PRIMER_CONTAINER_NAME')
INDEL_PRIMER_TASK_QUEUE_NAME = os.environ.get('INDEL_PRIMER_TASK_QUEUE_NAME')
MODULE_API_PIPELINE_TASK_URL_NAME = os.environ.get('MODULE_API_PIPELINE_TASK_URL_NAME')

API_PIPELINE_TASK_URL = get_secret(MODULE_API_PIPELINE_TASK_URL_NAME)

# =========================== #
#    pairwise_indel_finder    #
# =========================== #

MIN_SV_SIZE = 50
MAX_SV_SIZE = 500

# Initial load of strain list from sv_data
# This is run when the server is started.
# NOTE: Tabix cannot make requests over https!
SV_BED_URL = f"http://storage.googleapis.com/{MODULE_SITE_BUCKET_PRIVATE_NAME}/tools/pairwise_indel_primer/sv.20200815.bed.gz"
SV_VCF_URL = f"http://storage.googleapis.com/{MODULE_SITE_BUCKET_PRIVATE_NAME}/tools/pairwise_indel_primer/sv.20200815.vcf.gz"

SV_STRAINS = VCF(SV_VCF_URL).samples
SV_COLUMNS = ["CHROM",
              "START",
              "END",
              "SUPPORT",
              "SVTYPE",
              "STRAND",
              "SV_TYPE_CALLER",
              "SV_POS_CALLER",
              "STRAIN",
              "CALLER",
              "GT",
              "SNPEFF_TYPE",
              "SNPEFF_PRED",
              "SNPEFF_EFF",
              "SVTYPE_CLEAN",
              "TRANSCRIPT",
              "SIZE",
              "HIGH_EFF",
              "WBGeneID"]

STRAIN_CHOICES = [(x, x) for x in SV_STRAINS]
CHROMOSOME_CHOICES = [(x, x) for x in CHROM_NUMERIC.keys()]
COLUMNS = ["CHROM", "START", "STOP", "?", "TYPE", "STRAND", ""]

def get_indel_primer(id):
  return IndelPrimer(id)

def get_sv_strains():
  return SV_STRAINS

def get_user_indel_primers(username):
  logger.debug(f'Getting all indel primers for user: username:{username}')
  filters = [('username', '=', username)]
  results = query_ds_entities(IndelPrimer.kind, filters=filters)
  primers = [IndelPrimer(e) for e in results]
  return sorted(primers, key=lambda x: x.created_on, reverse=True)


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


def query_indels_and_mark_overlaps(strain1, strain2, chromosome, start, stop):
  results = []
  strain_cmp = [strain1,
                strain2]
  tb = tabix.open(SV_BED_URL)
  query = tb.query(chromosome, start, stop)
  results = []
  for row in query:
    row = dict(zip(SV_COLUMNS, row))
    row["START"] = int(row["START"])
    row["END"] = int(row["END"])
    if row["STRAIN"] in strain_cmp and \
      MIN_SV_SIZE <= int(row["SIZE"]) <= MAX_SV_SIZE:
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


def create_new_indel_primer(username, site, strain1, strain2, size, data_hash):
  logger.debug(f'Creating new Indel Primer: username:{username} site:{site} strain1:{strain1} strain2:{strain2} size:{size} data_hash:{data_hash}')
  id = unique_id()
  
  # Load container version info 
  c = get_current_container_version(INDEL_PRIMER_CONTAINER_NAME)
  
  status = 'SUBMITTED'
  props = {'id': id,
          'username': username,
          'site': site,
          'strain1': strain1,
          'strain2': strain2,
          'size': size,
          'data_hash': data_hash,
          'container_repo': c.repo,
          'container_name': c.container_name,
          'container_version': c.container_tag,
          'status': status}
  
  ip = IndelPrimer(id)
  ip.set_properties(**props)
  ip.save()

  data = {'site': site,
          'strain1': strain1,
          'strain2': strain2,
          'size': size}
  
  # TODO: assign remaining properties from cached result if it exists
  if check_blob_exists(ip.get_bucket_name(), ip.get_result_blob_path()):
    ip.status = 'COMPLETE'
    ip.save()
    return ip
  
  # Upload data.tsv to google storage
  bucket = ip.get_bucket_name()
  blob = ip.get_data_blob_path()
  upload_blob_from_string(bucket, json.dumps(data), blob)
  
  # Schedule mapping in task queue
  task = _create_indel_primer_task(ip)
  payload = task.get_payload()
  task = add_task(INDEL_PRIMER_TASK_QUEUE_NAME, f'{API_PIPELINE_TASK_URL}/task/start/{INDEL_PRIMER_TASK_QUEUE_NAME}', payload)
  if not task:
    ip.status = 'ERROR'
    ip.save()
  return ip


def _create_indel_primer_task(ip):
  return IndelPrimerTask(**{'id': ip.id,
                            'kind': IndelPrimer.kind,
                            'strain1': ip.strain1,
                            'strain2': ip.strain2,
                            'site': ip.site,
                            'data_hash': ip.data_hash,
                            'container_name': ip.container_name,
                            'container_version': ip.container_version,
                            'container_repo': ip.container_repo})


def update_indel_primer_status(id: str, status: str=None, operation_name: str=None):
  logger.debug(f'update_indel_primer_status: id:{id} status:{status} operation_name:{operation_name}')
  m = IndelPrimer(id)
  if status:
    m.set_properties(status=status)
  if operation_name:
    m.set_properties(operation_name=operation_name)
    
  m.save()
  return m