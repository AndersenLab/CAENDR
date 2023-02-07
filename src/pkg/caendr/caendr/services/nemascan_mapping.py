import os

from caendr.services.logger import logger

from caendr.models.datastore import NemascanMapping
from caendr.models.error     import DuplicateDataError, CachedDataError, NotFoundError

from caendr.services.cloud.storage import get_blob_list
from caendr.services.tools.submit import submit_job

NEMASCAN_NXF_CONTAINER_NAME = os.environ.get('NEMASCAN_NXF_CONTAINER_NAME')



def is_data_cached(ns: NemascanMapping):
  # Check if the file already exists in google storage (matching hash)
  data_exists = get_blob_list(ns.get_bucket_name(), ns.get_data_blob_path())
  if data_exists and len(data_exists) > 0:
    return True
  return False


def get_mapping(id):
  '''
    Get the Nemascan Mapping with the given ID.
    If no such report exists, returns None.
  '''

  logger.debug(f'Getting mapping: {id}')

  # Run the query
  m = NemascanMapping.get_ds(id)

  # If no matching Nemascan Mapping was found, return None
  if not m:
    return None

  # Otherwise, construct and add the report path if applicable
  if m.status != 'COMPLETE' and m.status != 'ERROR':
    report_path = get_report_blob_path(m)
    logger.debug(report_path)
    if report_path:
      m.set_properties(report_path=report_path, status='COMPLETE')
      m.save()

  # Return the mapping Entity
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



def create_new_mapping(user, data, no_cache=False):

  # Try to submit a new job
  try:
    return submit_job(NemascanMapping, user, data, no_cache=no_cache)

  # If same job submitted by this user, redirect to their prior submission
  except DuplicateDataError as e:
    logger.debug('User resubmitted identical nemascan mapping data')
    os.remove(data['filepath'])
    raise e

  # If same job submitted by a different user, associate new job with the cached data
  except CachedDataError as e:
    logger.debug('Nemascan Mapping with identical Data Hash exists. Returning cached report.')

    # Remove the local file
    os.remove(data['filepath'])

    # Add the report path to the Entity and save it
    new_report = e.args[0]
    new_report['report_path'] = get_report_blob_path(new_report)
    new_report.save()

    # Re-raise the edited Entity
    raise CachedDataError(new_report)



def update_nemascan_mapping_status(id: str, status: str=None, operation_name: str=None):
  logger.debug(f'update_nemascan_mapping_status: id:{id} status:{status} operation_name:{operation_name}')

  m = NemascanMapping.get_ds(id)
  if m is None:
    raise NotFoundError(f'No Nemascan Mapping with ID "{id}" was found.')

  if status:
    m.set_properties(status=status)
  if operation_name:
    m.set_properties(operation_name=operation_name)

  report_path = get_report_blob_path(m)
  if report_path:
    m.set_properties(report_path=report_path, status='COMPLETE')

  m.save()
  return m



# TODO: Move to NemascanMapping function / property?
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