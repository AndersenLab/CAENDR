import os
import csv

from logzero import logger

from caendr.models.task import NemaScanTask
from caendr.models.datastore import NemascanMapping
from caendr.utils.data import unique_id
from caendr.models.error import DataFormatError, DuplicateDataError
from caendr.services.cloud.storage import check_blob_exists, upload_blob_from_file
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

# TODO: write this
'''def is_mapping_cached(data_hash: str, container_name: str, container_version: str):
  filters = [('data_hash', '=', data_hash), 
            ('container_name', '=', container_name),
            ('container_version', '=', container_version)]
  e = query_ds_entities(Profile.kind, filters=filters)
  if e:
    logger.debug(e)
    return e
  '''
  
def get_mapping(id):
  return NemascanMapping(id)


def get_user_mappings(username):
  logger.debug(f'Getting all mappings for user: username:{username}')
  filters = [('username', '=', username)]
  results = query_ds_entities(NemascanMapping.kind, filters=filters)
  mappings = [NemascanMapping(e) for e in results]
  mappings = sorted(mappings, key=lambda x: x.created_on, reverse=True)
  return mappings
  
  
def create_new_mapping(username, label, file):
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
  
  m = NemascanMapping(id)
  m.set_properties(**props)
  m.save()

  # Upload data.tsv to google storage
  bucket = NemascanMapping.get_bucket_name()
  blob = m.get_data_blob_path()
  upload_blob_from_file(bucket, local_path, blob)
  os.remove(local_path)
  
  # Schedule mapping in task queue
  task = create_nemascan_mapping_task(m)
  payload = task.get_payload()
  task = add_task(NEMASCAN_TASK_QUEUE_NAME, F'{API_PIPELINE_TASK_URL}/task/start/{NEMASCAN_TASK_QUEUE_NAME}', payload)
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
    m.set_properties(gls_operation=operation_name)
    
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