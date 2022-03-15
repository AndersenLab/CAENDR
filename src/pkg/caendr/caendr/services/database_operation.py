import os
from logzero import logger
from sqlalchemy import func 

from caendr.models.datastore import DatabaseOperation
from caendr.models.task import DatabaseOperationTask
from caendr.models.sql import Homolog, StrainAnnotatedVariant, Strain, WormbaseGene, WormbaseGeneSummary
from caendr.services.tool_versions import GCR_REPO_NAME
from caendr.services.cloud.datastore import get_ds_entity, query_ds_entities
from caendr.services.cloud.task import add_task
from caendr.services.cloud.secret import get_secret
from caendr.utils.data import unique_id


MODULE_DB_OPERATIONS_CONTAINER_NAME = os.environ.get('MODULE_DB_OPERATIONS_CONTAINER_NAME')
MODULE_DB_OPERATIONS_CONTAINER_VERSION = os.environ.get('MODULE_DB_OPERATIONS_CONTAINER_VERSION')
MODULE_DB_OPERATIONS_TASK_QUEUE_NAME = os.environ.get('MODULE_DB_OPERATIONS_TASK_QUEUE_NAME')
MODULE_API_PIPELINE_TASK_URL_NAME = os.environ.get('MODULE_API_PIPELINE_TASK_URL_NAME')

API_PIPELINE_TASK_URL = get_secret(MODULE_API_PIPELINE_TASK_URL_NAME)

DB_OPS = {
  'DROP_AND_POPULATE_STRAINS': 'Rebuild strain table from google sheet',
  'DROP_AND_POPULATE_WORMBASE_GENES': 'Rebuild wormbase gene table from external sources',
  'DROP_AND_POPULATE_STRAIN_ANNOTATED_VARIANTS': 'Rebuild Strain Annotated Variant table from .csv.gz file',
  'DROP_AND_POPULATE_ALL_TABLES': 'Rebuild All Tables',
  'TEST_ECHO': 'Test ETL - Echo',
  'TEST_MOCK_DATA': 'Test ETL - Mock Data '
}


def get_all_db_ops(keys_only=False, order=None, placeholder=True):
  logger.debug(f'get_all_db_ops(keys_only={keys_only}, order={order})')
  ds_entities = query_ds_entities(DatabaseOperation.kind, keys_only=keys_only, order=order)
  logger.debug(ds_entities)
  return ds_entities

def get_count(q):
    count_q = q.statement.with_only_columns([func.count()]).order_by(None)
    count = q.session.execute(count_q).scalar()
    return count

def get_table_count(model):
  session = model.query.session
  query = f"SELECT reltuples AS estimate FROM pg_class where relname = '{model.__tablename__}';"
  result = session.execute(query).fetchone()
  return result[0]

def get_all_db_stats():
  # d = {
  #   'Homolog': get_count(Homolog.query),
  #   'StrainAnnotatedVariant': get_count(StrainAnnotatedVariant.query),
  #   'Strain': get_count(Strain.query),
  #   'WormbaseGene': get_count(WormbaseGene.query),
  #   'WormbaseGeneSummary': get_count(WormbaseGeneSummary.query)
  # }

  models = [Homolog, StrainAnnotatedVariant, Strain, WormbaseGene, WormbaseGeneSummary]

  stats = [ [model.__tablename__, get_table_count(model)] for model in models]

  return stats

  

  homolog_count = get_count(Homolog.query)
  logger.info(f'homolog_count: {homolog_count}')
  strain_annotated_variant_count = get_count(StrainAnnotatedVariant.query)
  logger.info(f'strain_annotated_variant_count: {strain_annotated_variant_count}')
  wormbase_gene_count = get_count(WormbaseGene.query)
  logger.info(f'wormbase_gene_count: {wormbase_gene_count}')
  wormbase_gene_summary_count = get_count(WormbaseGeneSummary.query)
  logger.info(f'wormbase_gene_summary_count: {wormbase_gene_summary_count}')
  strain_count = get_count(Strain.query)
  logger.info(f'strain_count: {strain_count}')
  
  d = {
    'Homolog': homolog_count,
    'StrainAnnotatedVariant': strain_annotated_variant_count,
    'Strain': strain_count,
    'WormbaseGene': wormbase_gene_count,
    'WormbaseGeneSummary': wormbase_gene_summary_count
  }
  return d


def get_etl_op(op_id, keys_only=False, order=None, placeholder=True):
  logger.debug(f'get_etl_op(op_id={op_id}, keys_only={keys_only}, order={order})')
  op = get_ds_entity(DatabaseOperation.kind, op_id)
  logger.debug(op)
  return op
      
def get_db_op_form_options(): 
  return [(key, val) for key, val in DB_OPS.items()]
  
  
def create_new_db_op(op, username, email, args=None, note=None):
  logger.debug(f'Creating new Database Operation: op:{op}, username:{username}, email:{email}, args:{args}, note:{note}')
  
  id = unique_id()
  props = {'id': id,
          'note': note, 
          'args': args,
          'db_operation': op,
          'username': username,
          'email': email,
          'container_repo': GCR_REPO_NAME,
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
                                  'username': d.username, 
                                  'email': d.email,
                                  'container_name': d.container_name,
                                  'container_version': d.container_version,
                                  'container_repo': d.container_repo})
  
  

def update_db_op_status(id: str, status: str=None, operation_name: str=None):
  logger.debug(f'update_db_op_status: id:{id} status:{status} operation_name:{operation_name}')
  d = DatabaseOperation(id)
  if status:
    d.set_properties(status=status)
  if operation_name:
    d.set_properties(operation_name=operation_name)
    
  d.save()
  return d
  
