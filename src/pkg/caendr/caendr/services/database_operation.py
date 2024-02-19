from sqlalchemy import func 

from caendr.services.logger           import logger
from caendr.utils.env                 import get_env_var

from caendr.models.datastore          import DatabaseOperation
from caendr.models.sql                import DbOp, ALL_SQL_TABLES
from caendr.services.cloud.datastore  import get_ds_entity, query_ds_entities
from caendr.services.cloud.postgresql import rollback_on_error


MODULE_DB_OPERATIONS_BUCKET_NAME       = get_env_var('MODULE_DB_OPERATIONS_BUCKET_NAME')
MODULE_DB_OPERATIONS_CONTAINER_NAME    = get_env_var('MODULE_DB_OPERATIONS_CONTAINER_NAME')
MODULE_DB_OPERATIONS_CONTAINER_VERSION = get_env_var('MODULE_DB_OPERATIONS_CONTAINER_VERSION')



#
# Retrieving ETL Op Entities
#

# TODO: Should this return DatabaseOperation entity objects?
def get_all_db_ops(keys_only=False, order=None, placeholder=True):
  logger.debug(f'get_all_db_ops(keys_only={keys_only}, order={order})')
  ds_entities = query_ds_entities(DatabaseOperation.kind, keys_only=keys_only, order=order)
  # logger.debug(ds_entities)
  return ds_entities

def get_etl_op(op_id, keys_only=False, order=None, placeholder=True):
  logger.debug(f'get_etl_op(op_id={op_id}, keys_only={keys_only}, order={order})')
  op = get_ds_entity(DatabaseOperation.kind, op_id)
  logger.debug(op)
  return op


#
# Computing SQL Table Stats
#

def get_count(q):
    count_q = q.statement.with_only_columns([func.count()]).order_by(None)
    count = q.session.execute(count_q).scalar()
    return count

@rollback_on_error
def get_table_count(model):
  session = model.query.session
  query = f"SELECT reltuples AS estimate FROM pg_class where relname = '{model.__tablename__}';"
  result = session.execute(query).fetchone()
  return result[0]

def get_table_count_safe(model):
  try:
    return get_table_count(model)
  except Exception as ex:
    logger.warning(f'Error getting count for table {model}: {ex}')
    return None

def get_all_db_stats():
  stats = [ [model.__tablename__, get_table_count_safe(model)] for model in ALL_SQL_TABLES ]
  return stats


#
# Db Op Forms
#

def get_db_op_form_options(): 
  return [ (op_type.value, DbOp.get_title(op_type)) for op_type in DbOp ]
