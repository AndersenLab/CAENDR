import os
import io
import pandas as pd

from caendr.services.logger import logger

from caendr.models.error import CachedDataError, DuplicateDataError, NotFoundError, EmptyReportDataError, EmptyReportResultsError, UnfinishedReportError
from caendr.models.datastore import HeritabilityReport

from caendr.services.cloud.storage import get_blob
from caendr.services.tools.submit import submit_job


HERITABILITY_CONTAINER_NAME = os.environ.get('HERITABILITY_CONTAINER_NAME')



def get_heritability_report(id):
  '''
    Get the Heritability Report with the given ID.
    If no such report exists, returns None.
  '''
  return HeritabilityReport.get_ds(id)



def get_all_heritability_results():
  logger.debug(f'Getting all heritability reports...')
  results = HeritabilityReport.query_ds()
  return HeritabilityReport.sort_by_created_date(results, reverse=True)



def get_user_heritability_results(username):
  logger.debug(f'Getting all heritability reports for user: username:{username}')
  filters = [('username', '=', username)]
  results = HeritabilityReport.query_ds(filters=filters)
  return HeritabilityReport.sort_by_created_date(results, reverse=True)



def create_new_heritability_report(user, data, no_cache=False):

  try:
    return submit_job(HeritabilityReport, user, data, no_cache=no_cache)

  # If same job submitted by this user, redirect to that report
  except DuplicateDataError as ex:
    logger.debug('User resubmitted identical heritability report data')
    raise ex

  # If same job submitted by a different user, point new report to cached results
  except CachedDataError as ex:
    logger.debug('Heritability Report with identical Data Hash exists. Returning cached report.')
    raise ex



def update_heritability_report_status(id: str, status: str=None, operation_name: str=None):
  logger.debug(f'update_heritability_report_status: id:{id} status:{status} operation_name:{operation_name}')

  h = HeritabilityReport.get_ds(id)
  if h is None:
    raise NotFoundError(f'No Heritability Report with ID "{id}" was found.')

  if status:
    h.set_properties(status=status)
  if operation_name:
    h.set_properties(operation_name=operation_name)
    
  h.save()
  return h



def fetch_heritability_report(report):

  # Get blob paths
  data_blob   = report.get_data_blob_path()
  result_blob = report.get_result_blob_path()

  data   = get_blob(report.get_bucket_name(), data_blob)
  result = get_blob(report.get_bucket_name(), result_blob)

  # If no submission file exists, return error
  if data is None:
    raise EmptyReportDataError(report.id)

  # Parse data file
  data = data.download_as_string().decode('utf-8')
  data = pd.read_csv(io.StringIO(data), sep="\t")
  data['AssayNumber'] = data['AssayNumber'].astype(str)
  data['label'] = data.apply(lambda x: f"{x['AssayNumber']}: {x['Value']}", 1)
  data = data.to_dict('records')

  # If results file is empty, report is unfinished
  # TODO: will get_blob always return None if empty?
  if not result:
    raise UnfinishedReportError(report.id, data=data)

  # Parse results file
  # TODO: Check for empty/error results file?
  result = result.download_as_string().decode('utf-8')
  result = pd.read_csv(io.StringIO(result), sep="\t")
  result = result.to_dict('records')[0]

  # Return parsed data & result
  return data, result
