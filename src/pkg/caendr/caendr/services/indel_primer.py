import tabix
import os
import json

from cyvcf2 import VCF
from caendr.services.logger import logger

from caendr.models.datastore import Container, IndelPrimer
from caendr.models.species import SPECIES_LIST
from caendr.models.task import IndelPrimerTask

from caendr.services.cloud.storage import upload_blob_from_string, get_blob, check_blob_exists

from caendr.utils.constants import CHROM_NUMERIC
from caendr.utils.data import unique_id



MODULE_SITE_BUCKET_PRIVATE_NAME   = os.environ.get('MODULE_SITE_BUCKET_PRIVATE_NAME')
INDEL_PRIMER_CONTAINER_NAME       = os.environ.get('INDEL_PRIMER_CONTAINER_NAME')
INDEL_PRIMER_TOOL_PATH            = os.environ.get('INDEL_PRIMER_TOOL_PATH')



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
  return IndelPrimer(id)


def get_all_indel_primers():
  logger.debug(f'Getting all indel primers...')
  primers = IndelPrimer.query_ds()
  return IndelPrimer.sort_by_created_date(primers, reverse=True)


def get_user_indel_primers(username):
  logger.debug(f'Getting all indel primers for user: username:{username}')
  filters = [('username', '=', username)]
  primers = IndelPrimer.query_ds(filters=filters)
  return IndelPrimer.sort_by_created_date(primers, reverse=True)


def get_bed_url(species, release = None):
  release = release or SPECIES_LIST[species].indel_primer_ver
  filename = IndelPrimer.get_source_filename(species, release)
  return f"http://storage.googleapis.com/{MODULE_SITE_BUCKET_PRIVATE_NAME}/{INDEL_PRIMER_TOOL_PATH}/{filename}.bed.gz"

def get_vcf_url(species, release = None):
  release = release or SPECIES_LIST[species].indel_primer_ver
  filename = IndelPrimer.get_source_filename(species, release)
  return f"http://storage.googleapis.com/{MODULE_SITE_BUCKET_PRIVATE_NAME}/{INDEL_PRIMER_TOOL_PATH}/{filename}.vcf.gz"


def get_sv_strains(species, release = None):
  release = release or SPECIES_LIST[species].indel_primer_ver
  return VCF( get_vcf_url( species, release ) ).samples


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

  tb = tabix.open( get_bed_url(species) )
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


def create_new_indel_primer(username, species, site, strain_1, strain_2, size, data_hash, no_cache=False):
  logger.debug(f'''Creating new Indel Primer:
    username:  "{username}"
    species:   {species}
    site:      {site}
    strain_1:  {strain_1}
    strain_2:  {strain_2}
    size:      {size}
    data_hash: {data_hash}
    cache:     {not no_cache}''')

  # Load container version info
  c = Container.get_current_version(INDEL_PRIMER_CONTAINER_NAME)

  # Check for existing indel primer matching data_hash & user
  if not no_cache:
    cached_submission = IndelPrimer.check_cached_submission(data_hash, username, c)
    if cached_submission:
      return cached_submission

  # Compute unique ID for new Indel Primer entity
  id = unique_id()

  # TODO: Pull this value from somewhere
  release = SPECIES_LIST[species].indel_primer_ver

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
    'species':           species,
    'release':           release,
    'container_repo':    c.repo,
    'container_name':    c.container_name,
    'container_version': c.container_tag,
    'sv_bed_filename':   IndelPrimer.get_source_filename(species, release) + '.bed.gz',
    'sv_vcf_filename':   IndelPrimer.get_source_filename(species, release) + '.vcf.gz',
  })
  ip.save()

  # Check if there is already a result
  if not no_cache:
    if ip.check_cached_result():
      ip.status = 'COMPLETE'
      ip.save()
      return ip

  # Collect data about this run
  data = {
    'site':     site,
    'strain_1': strain_1,
    'strain_2': strain_2,
    'size':     size,
    'species':  species,
    'release':  release,
  }

  # Upload data.tsv to google storage
  bucket = ip.get_bucket_name()
  blob = ip.get_data_blob_path()
  upload_blob_from_string(bucket, json.dumps(data), blob)

  # Schedule mapping in task queue
  task   = IndelPrimerTask(ip)
  result = task.submit()

  # Update entity status to reflect whether task was submitted successfully
  ip.status = 'SUBMITTED' if result else 'ERROR'
  ip.save()

  # Return resulting Indel Primer entity
  return ip



def update_indel_primer_status(id: str, status: str=None, operation_name: str=None):
  logger.debug(f'update_indel_primer_status: id:{id} status:{status} operation_name:{operation_name}')
  m = IndelPrimer(id)
  if status:
    m.set_properties(status=status)
  if operation_name:
    m.set_properties(operation_name=operation_name)
    
  m.save()
  return m