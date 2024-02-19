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

@rollback_on_error
def count_table_rows(model) -> int:
  '''
    Count the number of rows in a SQL table.

    Uses a more complicated query that's more efficient for big tables.
    Rolls back SQLAlchemy errors automatically.
  '''
  session   = model.query.session
  statement = model.query.statement.with_only_columns([func.count()]).order_by(None)
  return session.execute(statement).scalar()

# NOTE: This was the old way of getting the table count. Deprecated for being overly complex and potentially unsafe.
#       For some tables, it gives a slightly lower count than the direct query.count() method...
# @rollback_on_error
# def get_table_count(model):
#   session = model.query.session
#   query = f"SELECT reltuples AS estimate FROM pg_class where relname = '{model.__tablename__}';"
#   result = session.execute(query).fetchone()
#   return result[0]

def count_table_rows_safe(model):
  '''
    Count the number of rows in a SQL table.
    If any error is thrown, logs as a warning and returns `None` instead.
  '''

  # Try getting the count directly, handling any SQL errors
  try:
    return count_table_rows(model)

  # Log errors and return None
  except Exception as ex:
    logger.warning(f'Error getting count for table {model}: {ex}')
    return None


def get_all_db_stats():
  '''
    Count the rows in each table, and return all results.
    Returns `None` for any table that threw an error when trying to count the rows.
  '''
  return [ [model.__tablename__, count_table_rows_safe(model)] for model in ALL_SQL_TABLES ]


#
# Db Op Forms
#

def get_db_op_form_options(): 
  return [ (op_type.value, DbOp.get_title(op_type)) for op_type in DbOp ]
