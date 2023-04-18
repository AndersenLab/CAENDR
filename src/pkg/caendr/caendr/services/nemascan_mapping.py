import os

from caendr.services.logger import logger

from caendr.models.datastore import NemascanMapping
from caendr.models.error     import DuplicateDataError, CachedDataError, NotFoundError
from caendr.models.task      import TaskStatus

from caendr.services.cloud.storage import get_blob_list
from caendr.services.tools.submit import submit_job
from caendr.utils.env import get_env_var

NEMASCAN_NXF_CONTAINER_NAME = get_env_var('NEMASCAN_NXF_CONTAINER_NAME', can_be_none=True)



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
  return NemascanMapping.get_ds(id)


def get_mappings(username=None, filter_errs=False):
  '''
    Get a list of Mappings, sorted by most recent.

    Args:
      username (str | None):
        If provided, only return mappings owned by the given user.
      filter_errs (bool):
        If True, skips all entities that throw an error when initializing.
        If False, populates as many fields of those entities as possible.
  '''

  # Filter by username if provided, and log event accordingly
  if username:
    logger.debug(f'Getting all mappings for user: username:{username}')
    filters = [('username', '=', username)]
  else:
    logger.debug(f'Getting all mappings...')
    filters = []

  # Get list of mappings and filter by date
  mappings = NemascanMapping.query_ds(safe=not filter_errs, ignore_errs=filter_errs, filters=filters)
  return NemascanMapping.sort_by_created_date(mappings, reverse=True)



def create_new_mapping(user, data, no_cache=False):

  # Try to submit a new job
  try:
    return submit_job(NemascanMapping, user, data, no_cache=no_cache)

  # If same job submitted by this user, redirect to their prior submission
  except DuplicateDataError:
    logger.debug('User resubmitted identical nemascan mapping data')
    raise

  # If same job submitted by a different user, associate new job with the cached data
  except CachedDataError:
    logger.debug('Nemascan Mapping with identical Data Hash exists. Returning cached report.')
    raise



def update_nemascan_mapping_status(id: str, status: str=None, operation_name: str=None):
  logger.debug(f'update_nemascan_mapping_status: id:{id} status:{status} operation_name:{operation_name}')

  m = NemascanMapping.get_ds(id)
  if m is None:
    raise NotFoundError(f'No Nemascan Mapping with ID "{id}" was found.')

  if status:
    m.set_properties(status=status)
  if operation_name:
    m.set_properties(operation_name=operation_name)

  # Mark job as complete if report output file exists
  if m.report_path is not None:
    m['status'] = TaskStatus.COMPLETE

  m.save()
  return m







'''flash("Please make sure that your data file exactly matches the sample format", 'error')
    return redirect(url_for('mapping.mapping'))'''