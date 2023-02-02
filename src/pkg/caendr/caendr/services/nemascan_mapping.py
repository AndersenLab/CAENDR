import os
import csv

from caendr.services.logger import logger

from caendr.models.task import NemaScanTask
from caendr.models.datastore import NemascanMapping
from caendr.utils.data import unique_id
from caendr.models.error import DataFormatError, DuplicateDataError, CachedDataError
from caendr.services.cloud.storage import check_blob_exists, upload_blob_from_file, get_blob_list
from caendr.services.tool_versions import get_current_container_version
from caendr.utils.file import get_file_hash

from caendr.models.datastore import Container

NEMASCAN_NXF_CONTAINER_NAME = os.environ.get('NEMASCAN_NXF_CONTAINER_NAME')



uploads_dir = os.path.join('./', 'uploads')
os.makedirs(uploads_dir, exist_ok=True)


def is_data_cached(ns: NemascanMapping):
  # Check if the file already exists in google storage (matching hash)
  data_exists = get_blob_list(ns.get_bucket_name(), ns.get_data_blob_path())
  if data_exists and len(data_exists) > 0:
    return True
  return False


def get_mapping(id):
  logger.debug(f'Getting mapping: {id}')
  m = NemascanMapping(id)
  if not m:
    return None    
  if m.status != 'COMPLETE' and m.status != 'ERROR':
    report_path = get_report_blob_path(m)
    logger.debug(report_path)
    if report_path:
      m.set_properties(report_path=report_path, status='COMPLETE')
      m.save()
  return m


def get_all_mappings():
  logger.debug(f'Getting all mappings...')
  mappings = NemascanMapping.query_ds()
  return NemascanMapping.sort_by_created_date(mappings, reverse=True)


def get_user_mappings(username):
  logger.debug(f'Getting all mappings for user: username:{username}')
  filters = [('username', '=', username)]
  mappings = NemascanMapping.query_ds(filters=filters)
  return NemascanMapping.sort_by_created_date(mappings, reverse=True)
  
  
def create_new_mapping(username, email, label, file, species, status = 'SUBMITTED', check_duplicates=True):
  logger.debug(f'''Creating new Nemascan Mapping:
    username: "{username}"
    label:    "{label}"
    file:     {file}
    species:  {species}''')
  id = unique_id()

  # Save uploaded file to server temporarily
  local_path = os.path.join(uploads_dir, f'{id}.tsv')
  file.save(local_path)
  
  # Validate file format and extract details
  trait, data_hash = validate_data_format(id, local_path)
  
  # Load container version info 
  c = get_current_container_version(NEMASCAN_NXF_CONTAINER_NAME)
  
  # TODO: assign properties from cached mapping if it exists   if is_mapping_cached(data_hash):

  props = {
    'id': id,
    'username': username,
    'email': email,
    'label': label,
    'trait': trait,
    'species': species,
    'data_hash': data_hash,
    'container_repo': c.repo,
    'container_name': c.container_name,
    'container_version': c.container_tag,
    'status': status
  }
  
  
  m_new = NemascanMapping(id)

  if check_duplicates:
    logger.warn(f"Skipping Nemascan duplicate check")    
    # check for mappings with matching data hash and container version
    mappings = NemascanMapping.query_ds(filters=[('data_hash', '=', data_hash)])
    for m in mappings:
      if m.container_version == c.container_tag:
        if m.username == username:
          logger.debug('User resubmitted identical nemascan mapping data')
          os.remove(local_path)
          raise DuplicateDataError('You have already submitted this mapping data')
        else:
          logger.debug('Nemascan Mapping with identical Data Hash exists. Returning cached report.')
          props['status'] = m.status
          props['report_path'] = get_report_blob_path(m)
          m_new.set_properties(**props)
          m_new.save()
          os.remove(local_path)
          e = CachedDataError()
          e.description = id
          raise e

  m_new.set_properties(**props)
  m_new.save()
  
  # Upload data.tsv to google storage
  bucket = NemascanMapping.get_bucket_name()
  blob = m_new.get_data_blob_path()
  upload_blob_from_file(bucket, local_path, blob)
  os.remove(local_path)
  
  # Schedule mapping in task queue
  task   = NemaScanTask(m_new)
  result = task.submit()

  # Update entity status to reflect whether task was submitted successfully
  m_new.status = 'SUBMITTED' if result else 'ERROR'
  m_new.save()

  # Return resulting Nemascan Mapping entity
  return m_new



def update_nemascan_mapping_status(id: str, status: str=None, operation_name: str=None):
  logger.debug(f'update_nemascan_mapping_status: id:{id} status:{status} operation_name:{operation_name}')
  m = NemascanMapping(id)
  if status:
    m.set_properties(status=status)
  if operation_name:
    m.set_properties(operation_name=operation_name)
  
  report_path = get_report_blob_path(m)
  if report_path:
    m.set_properties(report_path=report_path, status='COMPLETE')

  m.save()
  return m



def validate_data_format(id, local_path):
  logger.debug(f'Validating Nemascan Mapping data format: id:{id}')

  # Read first line from tsv
  with open(local_path, 'r') as f:
    csv_reader = csv.reader(f, delimiter='\t')
    csv_headings = next(csv_reader)

  # Check first line for column headers (strain, {TRAIT})
  if csv_headings[0].lower() != 'strain' or len(csv_headings) != 2 or len(csv_headings[1]) == 0:
    raise DataFormatError()
  
  trait = csv_headings[1].lower()
  data_hash = get_file_hash(local_path, length=32)
  return trait, data_hash


def get_report_blob_path(m: NemascanMapping):
  logger.debug(f'Looking for a NemaScan Mapping HTML report: m:{m}')
  result = list(get_blob_list(m.get_bucket_name(), m.get_report_blob_prefix()))
  logger.debug(result)

  if len(result) > 0:
    for x in result:
      logger.debug(x.name)
      if x.name.endswith('.html'):
        return x.name
        





'''flash("Please make sure that your data file exactly matches the sample format", 'error')
    return redirect(url_for('mapping.mapping'))'''