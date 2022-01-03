import os
import csv

from logzero import logger

from caendr.models.task import NemaScanTask
from caendr.models.datastore import NemascanMapping
from caendr.utils.data import unique_id
from caendr.models.error import DataFormatError, DuplicateDataError
from caendr.services.cloud.storage import check_blob_exists, upload_blob_from_file, get_blob_list
from caendr.services.cloud.datastore import query_ds_entities
from caendr.services.cloud.task import add_task
from caendr.services.cloud.secret import get_secret
from caendr.services.tool_versions import get_current_container_version
from caendr.utils.file import get_file_hash

NEMASCAN_NXF_CONTAINER_NAME = os.environ.get('NEMASCAN_NXF_CONTAINER_NAME')
NEMASCAN_TASK_QUEUE_NAME = os.environ.get('NEMASCAN_TASK_QUEUE_NAME')
MODULE_API_PIPELINE_TASK_URL_NAME = os.environ.get('MODULE_API_PIPELINE_TASK_URL_NAME')

API_PIPELINE_TASK_URL = get_secret(MODULE_API_PIPELINE_TASK_URL_NAME)


uploads_dir = os.path.join('./', 'uploads')
os.makedirs(uploads_dir, exist_ok=True)


def is_data_cached(ns: NemascanMapping):
  # Check if the file already exists in google storage (matching hash)
  data_exists = get_blob_list(ns.get_bucket_name(), ns.get_data_blob_path())
  if data_exists and len(data_exists) > 0:
    return True
  return False


def is_result_cached(ns: NemascanMapping):
  if ns.status == 'COMPLETE' and len(ns.report_path) > 0:
    return True

  result = get_blob_list(ns.get_bucket_name(), ns.get_report_blob_path())

  # check if there is a report on GS, just to be sure
  if len(result) > 0:
    for x in result:
      if x.name.endswith('.html'):
        report_path = x.name
        ns.report_path = report_path
        ns.status = 'COMPLETE'
        ns.save()
        return True


def get_mapping(id):
  return NemascanMapping(id)


def get_user_mappings(username):
  logger.debug(f'Getting all mappings for user: username:{username}')
  filters = [('username', '=', username)]
  results = query_ds_entities(NemascanMapping.kind, filters=filters)
  mappings = [NemascanMapping(e) for e in results]
  mappings = sorted(mappings, key=lambda x: x.created_on, reverse=True)
  return mappings
  
  
def create_new_mapping(username, label, file, status):
  logger.debug(f'Creating new Nemascan Mapping: username:{username} label:{label} file:{file}')
  id = unique_id()

  # Save uploaded file to server temporarily
  local_path = os.path.join(uploads_dir, f'{id}.tsv')
  file.save(local_path)
  
  # Validate file format and extract details
  trait, data_hash = validate_data_format(id, local_path)
  
  # Load container version info 
  c = get_current_container_version(NEMASCAN_NXF_CONTAINER_NAME)
  
  # TODO: assign properties from cached mapping if it exists   if is_mapping_cached(data_hash):

  props = {'id': id,
          'username': username,
          'label': label,
          'trait': trait,
          'data_hash': data_hash,
          'container_repo': c.repo,
          'container_name': c.container_name,
          'container_version': c.container_tag,
          'status': 'SUBMITTED'}
  
  # Check for an existing nemascan mapping owned by the same user that matches the data_hash and container tag. Updates the label.
  mappings = query_ds_entities(NemascanMapping.kind, filters=[('data_hash', '=', data_hash)])
  for m in mappings:
    m = NemascanMapping(m)
    if m.username == username and m.container_version == c.container_tag:
      m.label = label
      m.save()
      logger.debug('Nemascan Mapping with identical Data already submitted by this user. Returning cached results.')
      return m
  
  m = NemascanMapping(id)
  m.set_properties(**props)
  m.save()
  
  m = NemascanMapping(id)
  # Check if there is already cached data from another user
  if is_data_cached(m):
    m.set_properties({'status': 'DUPLICATE'})
    m.save()
    logger.debug('Nemascan Mapping with identical Data Hash already exists. Returning cached results.')
    return NemascanMapping(id)
  # TODO: Duplicate the cached results mapping status property
  
  # Check if there is already a cached result from another user
  if is_result_cached(m):
    m.set_properties({'status': 'COMPLETE'})
    m.save()
    logger.debug('Nemascan Mapping with identical Data Hash already exists. Returning cached results.')
    return NemascanMapping(id)

  # Upload data.tsv to google storage
  bucket = NemascanMapping.get_bucket_name()
  blob = m.get_data_blob_path()
  upload_blob_from_file(bucket, local_path, blob)
  os.remove(local_path)
  
  # Schedule mapping in task queue
  task = create_nemascan_mapping_task(m)
  payload = task.get_payload()
  task = add_task(NEMASCAN_TASK_QUEUE_NAME, f'{API_PIPELINE_TASK_URL}/task/start/{NEMASCAN_TASK_QUEUE_NAME}', payload)
  if not task:
    m.status = 'ERROR'
    m.save()
  return m
  
  
def create_nemascan_mapping_task(m):
  return NemaScanTask(**{'id': m.id,
                          'kind': NemascanMapping.kind,
                          'data_hash': m.data_hash,
                          'container_name': m.container_name,
                          'container_version': m.container_version,
                          'container_repo': m.container_repo})



def update_nemascan_mapping_status(id: str, status: str=None, operation_name: str=None):
  logger.debug(f'update_nemascan_mapping_status: id:{id} status:{status} operation_name:{operation_name}')
  m = NemascanMapping(id)
  if status:
    m.set_properties(status=status)
  if operation_name:
    m.set_properties(operation_name=operation_name)
    
  m.save()
  return m
  

  
def validate_data_format(id, local_path):
  logger.debug(f'Validating Nemascan Mapping data format: id:{id}')

  # Read first line from tsv
  with open(local_path, 'r') as f:
    csv_reader = csv.reader(f, delimiter='\t')
    csv_headings = next(csv_reader)

  # Check first line for column headers (strain, {TRAIT})
  if csv_headings[0] != 'strain' or len(csv_headings) != 2 or len(csv_headings[1]) == 0:
    raise DataFormatError()
  
  trait = csv_headings[1]
  data_hash = get_file_hash(local_path, length=32)
  return trait, data_hash




'''flash("Please make sure that your data file exactly matches the sample format", 'error')
    return redirect(url_for('mapping.mapping'))'''