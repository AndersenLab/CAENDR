import os
import json

from caendr.services.logger import logger

from caendr.services.cloud.storage import upload_blob_from_string, generate_blob_url, check_blob_exists
from caendr.models.task import HeritabilityTask
from caendr.models.error import CachedDataError, DuplicateDataError
from caendr.models.datastore import Container, HeritabilityReport
from caendr.utils.data import convert_data_table_to_tsv, get_object_hash


HERITABILITY_CONTAINER_NAME = os.environ.get('HERITABILITY_CONTAINER_NAME')



def get_heritability_report(id):
  return HeritabilityReport(id)


def get_all_heritability_results():
  logger.debug(f'Getting all heritability reports...')
  results = HeritabilityReport.query_ds()
  return HeritabilityReport.sort_by_created_date(results, reverse=True)


def get_user_heritability_results(username):
  logger.debug(f'Getting all heritability reports for user: username:{username}')
  filters = [('username', '=', username)]
  results = HeritabilityReport.query_ds(filters=filters)
  return HeritabilityReport.sort_by_created_date(results, reverse=True)



def create_new_heritability_report(username, label, data_table):
  logger.debug(f'''Creating new Heritability Report:
    username: "{username}"
    label:    "{label}"''')

  # Load container version info 
  c = Container.get_current_version(HERITABILITY_CONTAINER_NAME)
  logger.debug(f"Creating heritability calculation with {c.uri()}")

  # Parse data table
  data_file, data_hash, data_vals = parse_heritability_data(data_table)

  # Create new Heritability Report entity
  h2_new = HeritabilityReport(**{
    'username': username,
    'label':    label,
    'trait':    data_vals['trait'],
    'status':   'SUBMITTED',
  })
  h2_new.set_container(c)
  h2_new.data_hash = data_hash


  # Check for cached results
  try:
    HeritabilityReport.check_cache(h2_new.data_hash, username, c, status = 'COMPLETE')

  # If same job submitted by this user, redirect to that report
  except DuplicateDataError as e:
    logger.debug('User resubmitted identical heritability report data')
    # DuplicateDataError('You have already submitted this heritability data')
    raise e

  # If same job submitted by a different user, point new report to cached results
  except CachedDataError as e:
    logger.debug('Heritability Report with identical Data Hash exists. Returning cached report.')
    h2_new.status = 'COMPLETE'
    h2_new.save()
    e.description = h2_new.id
    raise CachedDataError(h2_new)

  # If no existing report was found, save & submit this one
  h2_new.save()

  # Check if there is already a cached result from another user
  # TODO: This check is redundant, given the CachedDataError check above...
  if h2_new.check_cached_result():
    h2_new.status = 'COMPLETE'
    h2_new.save()
    return HeritabilityReport(h2_new.id)

  # Upload data.tsv to google storage
  bucket = h2_new.get_bucket_name()
  blob = h2_new.get_data_blob_path()
  upload_blob_from_string(bucket, data_file, blob)

  # Schedule mapping in task queue
  task   = HeritabilityTask(h2_new)
  result = task.submit()

  # Update entity status to reflect whether task was submitted successfully
  h2_new.status = 'SUBMITTED' if result else 'ERROR'
  h2_new.save()

  # Return resulting Heritability Report entity
  return h2_new



def update_heritability_report_status(id: str, status: str=None, operation_name: str=None):
  logger.debug(f'update_heritability_report_status: id:{id} status:{status} operation_name:{operation_name}')
  h = HeritabilityReport(id)
  if status:
    h.set_properties(status=status)
  if operation_name:
    h.set_properties(operation_name=operation_name)
    
  h.save()
  return h



def parse_heritability_data(table_data):

  # Extract table data
  data = json.loads(table_data)
  data = [x for x in data[1:] if x[0] is not None]

  # Create TSV file for upload
  columns = ["AssayNumber", "Strain", "TraitName", "Replicate", "Value"]
  data_file = convert_data_table_to_tsv(data, columns)

  data_hash = get_object_hash(data, length=32)

  # Extract trait from table data
  trait = data[0][2]

  return data_file, data_hash, {'trait': trait}
