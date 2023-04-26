import os
import io
import pandas as pd

from caendr.services.logger import logger

from caendr.models.error import NotFoundError, EmptyReportDataError, EmptyReportResultsError, UnfinishedReportError
from caendr.models.datastore import HeritabilityReport

from caendr.services.cloud.storage import get_blob
from caendr.services.tools.submit import submit_job
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



def update_heritability_report_status(id: str, status: str=None, operation_name: str=None):
  logger.debug(f'update_heritability_report_status: id:{id} status:{status} operation_name:{operation_name}')

  h = HeritabilityReport.get_ds(id)
  if h is None:
    raise NotFoundError(HeritabilityReport, {'id': id})

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
