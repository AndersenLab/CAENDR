import os

from logzero import logger

from caendr.services.cloud.datastore import query_ds_entities
from caendr.services.cloud.storage import upload_blob_from_string, generate_blob_url, check_blob_exists
from caendr.models.task import HeritabilityTask
from caendr.models.datastore import HeritabilityReport
from caendr.utils.data import unique_id
from caendr.services.cloud.task import add_task
from caendr.services.cloud.secret import get_secret
from caendr.services.tool_versions import get_current_container_version


HERITABILITY_CONTAINER_NAME = os.environ.get('HERITABILITY_CONTAINER_NAME')
HERITABILITY_TASK_QUEUE_NAME = os.environ.get('HERITABILITY_TASK_QUEUE_NAME')
MODULE_API_PIPELINE_TASK_URL_NAME = os.environ.get('MODULE_API_PIPELINE_TASK_URL_NAME')

API_PIPELINE_TASK_URL = get_secret(MODULE_API_PIPELINE_TASK_URL_NAME)


def get_heritability_report(id):
  return HeritabilityReport(id)


def get_user_heritability_reports(username):
  logger.debug(f'Getting all heritability reports for user: username:{username}')
  filters = [('username', '=', username)]
  results = query_ds_entities(HeritabilityReport.kind, filters=filters)
  primers = [HeritabilityReport(e) for e in results]
  return sorted(primers, key=lambda x: x.created_on, reverse=True)


def create_new_heritability_report(username, label, data_hash, trait, data_tsv):
  logger.debug(f'Creating new Heritability Report: username:{username} label:{label} data_hash:{data_hash} trait:{trait}')
  id = unique_id()
  
  # Load container version info 
  c = get_current_container_version(HERITABILITY_CONTAINER_NAME)
  
  # TODO: assign properties from cached result if it exists
  status = 'SUBMITTED'
  props = {'id': id,
          'username': username,
          'label': label,
          'data_hash': data_hash,
          'trait': trait,
          'container_repo': c.repo,
          'container_name': c.container_name,
          'container_version': c.container_tag,
          'status': status}
  
  # Check for an existing heritability report owned by the same user that matches the data_hash and container tag. Updates the label.
  h2s = query_ds_entities(HeritabilityReport.kind, filters=[('data_hash', '=', data_hash)])
  for h2 in h2s:
    h2 = HeritabilityReport(h2)
    if h2.username == username and h2.container_version == c.container_tag:
      h2.label = label
      h2.save()
      return h2

  h2 = HeritabilityReport(id)
  h2.set_properties(**props)
  h2.save()
  
  # Check if there is already a cached result from another user
  if check_blob_exists(h2.get_bucket_name(), h2.get_result_blob_path()):
    h2.status = 'COMPLETE'
    h2.save()
    return h2
  
  # Upload data.tsv to google storage
  bucket = h2.get_bucket_name()
  blob = h2.get_data_blob_path()
  upload_blob_from_string(bucket, data_tsv, blob)

  # Schedule mapping in task queue
  task = _create_heritability_task(h2)
  payload = task.get_payload()
  task = add_task(HERITABILITY_TASK_QUEUE_NAME, f'{API_PIPELINE_TASK_URL}/task/start/{HERITABILITY_TASK_QUEUE_NAME}', payload)
  if not task:
    h2.status = 'ERROR'
    h2.save()
  return h2
  
  
def _create_heritability_task(h):
  return HeritabilityTask(**{'id': h.id,
                            'kind': HeritabilityReport.kind,
                            'data_hash': h.data_hash,
                            'container_name': h.container_name,
                            'container_version': h.container_version,
                            'container_repo': h.container_repo})



def update_heritability_report_status(id: str, status: str=None, operation_name: str=None):
  logger.debug(f'update_heritability_report_status: id:{id} status:{status} operation_name:{operation_name}')
  h = HeritabilityReport(id)
  if status:
    h.set_properties(status=status)
  if operation_name:
    h.set_properties(operation_name=operation_name)
    
  h.save()
  return h
