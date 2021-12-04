import os
from logzero import logger

from caendr.models.datastore import DatabaseOperation
from caendr.models.task import DatabaseOperationTask
from caendr.services.tool_versions import GCR_REPO
from caendr.services.cloud.datastore import query_ds_entities
from caendr.services.cloud.task import add_task
from caendr.services.cloud.secret import get_secret
from caendr.utils.data import unique_id


MODULE_DB_OPERATIONS_CONTAINER_NAME = os.environ.get('MODULE_DB_OPERATIONS_CONTAINER_NAME')
MODULE_DB_OPERATIONS_CONTAINER_VERSION = os.environ.get('MODULE_DB_OPERATIONS_CONTAINER_VERSION')
MODULE_DB_OPERATIONS_TASK_QUEUE_NAME = os.environ.get('MODULE_DB_OPERATIONS_TASK_QUEUE_NAME')
MODULE_API_PIPELINE_TASK_URL_NAME = os.environ.get('MODULE_API_PIPELINE_TASK_URL_NAME')

API_PIPELINE_TASK_URL = get_secret(MODULE_API_PIPELINE_TASK_URL_NAME)

DB_OPS = {'DROP_AND_POPULATE_STRAINS': 'Rebuild strain table from google sheet',
          'DROP_AND_POPULATE_WORMBASE_GENES': 'Rebuild wormbase gene table from external sources',
          'DROP_AND_POPULATE_HOMOLOGENES': 'Rebuild Homologene table from external sources',
          'DROP_AND_POPULATE_STRAIN_ANNOTATED_VARIANTS': 'Rebuild Strain Annotated Variant table from .csv.gz file',
          'DROP_AND_POPULATE_ALL_TABLES': 'Rebuild All Tables'}


def get_all_db_ops(keys_only=False, order=None, placeholder=True):
  logger.debug(f'get_all_db_ops(keys_only={keys_only}, order={order})')
  ds_entities = query_ds_entities(DatabaseOperation.kind, keys_only=keys_only, order=order)
  logger.debug(ds_entities)
  return [DatabaseOperation(e.key.name) for e in ds_entities]


def get_db_op_form_options(): 
  return [(key, val) for key, val in DB_OPS.items()]
  
  
def create_new_db_op(op, username, args=None, note=None):
  logger.debug(f'Creating new Database Operation: op:{op}, username:{username}, args:{args}, note:{note}')
  
  id = unique_id()
  props = {'id': id,
          'note': note, 
          'args': args,
          'db_operation': op,
          'username': username,
          'container_repo': GCR_REPO,
          'container_name': MODULE_DB_OPERATIONS_CONTAINER_NAME,
          'container_version': MODULE_DB_OPERATIONS_CONTAINER_VERSION}
  d = DatabaseOperation(id)
  d.set_properties(**props)
  d.save()
  
  # Schedule mapping in task queue
  task = _create_db_op_task(d)
  payload = task.get_payload()
  task = add_task(MODULE_DB_OPERATIONS_TASK_QUEUE_NAME, F'{API_PIPELINE_TASK_URL}/task/start/{MODULE_DB_OPERATIONS_TASK_QUEUE_NAME}', payload)
  d = DatabaseOperation(id)
  if task:
    d.set_properties(status='SUBMITTED')
  else:
    d.set_properties(status='ERROR')
  d.save()
  return d
  
  
def _create_db_op_task(d):
  return DatabaseOperationTask(**{'id': d.id,
                                  'kind': DatabaseOperation.kind,
                                  'db_operation': d.db_operation,
                                  'args': d.args,
                                  'container_name': d.container_name,
                                  'container_version': d.container_version,
                                  'container_repo': d.container_repo})
  
  

def update_db_op_status(id: str, status: str=None, operation_name: str=None):
  logger.debug(f'update_db_op_status: id:{id} status:{status} operation_name:{operation_name}')
  d = DatabaseOperation(id)
  if status:
    d.set_properties(status=status)
  if operation_name:
    d.set_properties(gls_operation=operation_name)
    
  d.save()
  return d
  
