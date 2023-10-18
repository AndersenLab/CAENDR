import os
from caendr.services.logger import logger
from sqlalchemy import func 

from caendr.models.datastore import DatabaseOperation, DbOp
from caendr.models.sql import Homolog, StrainAnnotatedVariant, Strain, WormbaseGene, WormbaseGeneSummary
from caendr.services.tool_versions import GCR_REPO_NAME
from caendr.services.cloud.datastore import get_ds_entity, query_ds_entities
from caendr.utils.data import unique_id
from caendr.utils.env import get_env_var


MODULE_DB_OPERATIONS_BUCKET_NAME       = get_env_var('MODULE_DB_OPERATIONS_BUCKET_NAME')
MODULE_DB_OPERATIONS_CONTAINER_NAME    = get_env_var('MODULE_DB_OPERATIONS_CONTAINER_NAME')
MODULE_DB_OPERATIONS_CONTAINER_VERSION = get_env_var('MODULE_DB_OPERATIONS_CONTAINER_VERSION')



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
  return [ (op_type.value, DbOp.get_title(op_type)) for op_type in DbOp ]
