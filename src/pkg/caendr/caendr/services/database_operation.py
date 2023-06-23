import os
from caendr.services.logger import logger
from sqlalchemy import func 

from caendr.models.datastore import DatabaseOperation, Container, SPECIES_LIST
from caendr.models.task import DatabaseOperationTask, TaskStatus
from caendr.models.sql import Homolog, StrainAnnotatedVariant, Strain, WormbaseGene, WormbaseGeneSummary
from caendr.services.tool_versions import GCR_REPO_NAME
from caendr.services.cloud.datastore import get_ds_entity, query_ds_entities
from caendr.services.cloud.storage import get_blob_list
from caendr.services.sql.dataset._env import internal_db_blob_templates
from caendr.utils.data import unique_id
from caendr.utils.env import get_env_var
from caendr.utils.tokens import TokenizedString


MODULE_DB_OPERATIONS_BUCKET_NAME       = get_env_var('MODULE_DB_OPERATIONS_BUCKET_NAME')
MODULE_DB_OPERATIONS_CONTAINER_NAME    = get_env_var('MODULE_DB_OPERATIONS_CONTAINER_NAME')
MODULE_DB_OPERATIONS_CONTAINER_VERSION = get_env_var('MODULE_DB_OPERATIONS_CONTAINER_VERSION')



DB_OPS = {

  ## Rebuild Tables ##

  'DROP_AND_POPULATE_STRAINS': {
    'title': 'Rebuild strain table from google sheet',
    'files': [],
  },
  'DROP_AND_POPULATE_WORMBASE_GENES': {
    'title': 'Rebuild wormbase gene table from external sources',
    'files': [
      internal_db_blob_templates['GENE_GFF'],
      internal_db_blob_templates['GENE_GTF'],
      internal_db_blob_templates['GENE_IDS'],
    ],
  },
  'DROP_AND_POPULATE_STRAIN_ANNOTATED_VARIANTS': {
    'title': 'Rebuild Strain Annotated Variant table from .csv.gz file',
    'files': [
      internal_db_blob_templates['SVA_CSVGZ'],
    ],
  },
  'DROP_AND_POPULATE_ALL_TABLES': {
    'title': 'Rebuild All Tables',
    'files': [
      internal_db_blob_templates['GENE_GFF'],
      internal_db_blob_templates['GENE_GTF'],
      internal_db_blob_templates['GENE_IDS'],
      internal_db_blob_templates['SVA_CSVGZ'],
    ],
  },

  ## Tests ##

  'TEST_ECHO': {
    'title': 'Test ETL - Echo',
    'files': [],
  },
  'TEST_MOCK_DATA': {
    'title': 'Test ETL - Mock Data',
    'files': [],
  },
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
  return [(key, val['title']) for key, val in DB_OPS.items()]


def db_op_preflight_check(op, species_list):
  '''
    Check that all files required for a given operation & species list are defined.
    Returns a list of all missing files.  If list is empty, no files are missing.
  '''

  op_config = DB_OPS.get(op)
  if op_config is None:
    raise Exception(f'Invalid operation name {op}')

  # Map list of species IDs to species objects
  if species_list is None or len(species_list) == 0:
    species_list = SPECIES_LIST.keys()
  species_list = [ SPECIES_LIST[key] for key in species_list ]

  # Get list of all filenames in db ops bucket
  all_files = [
    file.name for file in get_blob_list(MODULE_DB_OPERATIONS_BUCKET_NAME, '') if not file.name.endswith('/')
  ]

  # Loop through all required files, tracking those that don't appear in the database
  missing_files = []
  for file_template in op_config.get('files', []):
    for species in species_list:
      filepath = TokenizedString.replace_string(file_template, **{
        'SPECIES': species.name,
        'RELEASE': species['release_latest'],
        'SVA':     species['release_sva'],
      })
      if filepath not in all_files:
        missing_files.append(f'- {MODULE_DB_OPERATIONS_BUCKET_NAME}/{filepath}')

  # Return the list of missing files
  return missing_files


def create_new_db_op(op, user, args=None, note=None):
  logger.debug(f'Creating new Database Operation: op:{op}, user:{user}, args:{args}, note:{note}')

  # Get the DB Operations container from datastoer
  container = Container.get(MODULE_DB_OPERATIONS_CONTAINER_NAME)

  # Create Database Operation entity & upload to datastore
  db_op = DatabaseOperation(**{
    'note':              note,
    'db_operation':      op,
    'args':              args,
  })

  # Set entity's container & user fields
  db_op.set_container(container)
  db_op.set_user(user)

  # Upload the new entity to datastore
  db_op['status'] = TaskStatus.SUBMITTED
  db_op.save()

  # Schedule mapping in task queue
  task   = DatabaseOperationTask(db_op, email=db_op.get_user_email())
  result = task.submit()

  # Update entity status to reflect whether task was submitted successfully
  db_op.status = TaskStatus.SUBMITTED if result else TaskStatus.ERROR
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
  
