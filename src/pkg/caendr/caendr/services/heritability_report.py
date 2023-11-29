from caendr.services.logger import logger

from caendr.models.datastore import HeritabilityReport

from caendr.utils.env import get_env_var


HERITABILITY_CONTAINER_NAME = get_env_var('HERITABILITY_CONTAINER_NAME', can_be_none=True)



def get_heritability_report(id):
  '''
    Get the Heritability Report with the given ID.
    If no such report exists, returns None.
  '''
  return HeritabilityReport.get_ds(id)



def get_heritability_reports(username=None, filter_errs=False):
  '''
    Get a list of Heritability reports, sorted by most recent.

    Args:
      username (str | None):
        If provided, only return reports owned by the given user.
      filter_errs (bool):
        If True, skips all entities that throw an error when initializing.
        If False, populates as many fields of those entities as possible.
  '''
  # Filter by username if provided, and log event
  if username:
    logger.debug(f'Getting all heritability reports for user: username:{username}')
    filters = [('username', '=', username)]
  else:
    logger.debug(f'Getting all heritability reports...')
    filters = []

  # Get list of reports and filter by date
  results = HeritabilityReport.query_ds(safe=not filter_errs, ignore_errs=filter_errs, filters=filters)
  return HeritabilityReport.sort_by_created_date(results, reverse=True)
