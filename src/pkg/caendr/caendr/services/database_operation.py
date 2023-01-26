import os
from caendr.services.logger import logger
from sqlalchemy import func 

from caendr.models.datastore import DatabaseOperation
from caendr.models.task import DatabaseOperationTask
from caendr.models.sql import Homolog, StrainAnnotatedVariant, Strain, WormbaseGene, WormbaseGeneSummary
from caendr.services.tool_versions import GCR_REPO_NAME
from caendr.services.cloud.datastore import get_ds_entity, query_ds_entities
from caendr.utils.data import unique_id



MODULE_DB_OPERATIONS_CONTAINER_NAME = os.environ.get('MODULE_DB_OPERATIONS_CONTAINER_NAME')
MODULE_DB_OPERATIONS_CONTAINER_VERSION = os.environ.get('MODULE_DB_OPERATIONS_CONTAINER_VERSION')



DB_OPS = {
  'DROP_AND_POPULATE_STRAINS': 'Rebuild strain table from google sheet',
  'DROP_AND_POPULATE_WORMBASE_GENES': 'Rebuild wormbase gene table from external sources',
  'DROP_AND_POPULATE_STRAIN_ANNOTATED_VARIANTS': 'Rebuild Strain Annotated Variant table from .csv.gz file',
  'DROP_AND_POPULATE_ALL_TABLES': 'Rebuild All Tables',
  'TEST_ECHO': 'Test ETL - Echo',
  'TEST_MOCK_DATA': 'Test ETL - Mock Data '
}


# TODO: Should this return DatabaseOperation entity objects?
def get_all_db_ops(keys_only=False, order=None, placeholder=True):
  logger.debug(f'get_all_db_ops(keys_only={keys_only}, order={order})')
  ds_entities = query_ds_entities(DatabaseOperation.kind, keys_only=keys_only, order=order)
  # logger.debug(ds_entities)
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

  # Compute unique ID for new Database Operation entity
  id = unique_id()

  # Create Database Operation entity & upload to datastore
  db_op = DatabaseOperation(id, **{
    'id':                id,
    'username':          username,
    'email':             email,
    'note':              note,
    'db_operation':      op,
    'args':              args,
    'container_repo':    GCR_REPO_NAME,
    'container_name':    MODULE_DB_OPERATIONS_CONTAINER_NAME,
    'container_version': MODULE_DB_OPERATIONS_CONTAINER_VERSION,
  })
  db_op.save()

  # Schedule mapping in task queue
  task   = DatabaseOperationTask(db_op)
  result = task.submit()

  # Update entity status to reflect whether task was submitted successfully
  db_op.status = 'SUBMITTED' if result else 'ERROR'
  db_op.save()

  # Return resulting Database Operation entity
  return db_op



def update_db_op_status(id: str, status: str=None, operation_name: str=None):
  logger.debug(f'update_db_op_status: id:{id} status:{status} operation_name:{operation_name}')
  db_op = DatabaseOperation(id)
  if status:
    db_op.set_properties(status=status)
  if operation_name:
    db_op.set_properties(operation_name=operation_name)
    
  db_op.save()
  return db_op
  
