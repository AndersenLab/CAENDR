import os

from caendr.services.logger import logger

from base.utils.auth import get_current_user, user_is_admin

from constants import TOOL_INPUT_DATA_VALID_FILE_EXTENSIONS

from caendr.models.error import (
    CachedDataError,
    DataFormatError,
    DuplicateDataError,
    ReportLookupError,
)
from caendr.models.job_pipeline import JobPipeline, get_pipeline_class
from caendr.services.cloud.secret import get_secret



SUPPORT_EMAIL = get_secret('SUPPORT_EMAIL')


def get_upload_err_msg(code):
  CODE_TO_MSG = {
    400: 'You must include a CSV file with your data to upload. If this message persists, try refreshing the page and re-uploading your file.',
    500: f'There was a problem uploading your submission. Please try again. If this problem persists, please contact us at {SUPPORT_EMAIL}',
  }
  return CODE_TO_MSG.get(code, CODE_TO_MSG[500])


def lookup_report(kind, reportId, user=None, validate_user=True) -> JobPipeline:
  '''
    Create a JobPipeline object representing the report with the given ID and kind.
  '''

  # If no user explicitly provided, default to current user
  if validate_user and user is None:
    user = get_current_user()

  # Get & validate the job pipeline class from the provided kind
  try:
    JobPipelineClass = get_pipeline_class(kind=kind)
  except Exception as ex:
    logger.error(f'Error getting JobPipeline subclass: unknown kind "{kind}". Exception: {ex}')
    if user_is_admin() or not validate_user:
      raise ReportLookupError('Invalid report type.', 400)
    else:
      raise ReportLookupError('You do not have access to that report.', 401)

  # Retrieve the report entity from datastore, or None if no entity with that ID exists
  try:
    job = JobPipelineClass.lookup(reportId)

  # If no such report exists, show an error message
  except Exception:

    # Let admins know the report doesn't exist
    if user_is_admin() or not validate_user:
      raise ReportLookupError('This is not a valid report URL.', 404)

    # For all other users, display a default "no access" message
    else:
      raise ReportLookupError('You do not have access to that report.', 401)

  # If the user doesn't have permission to view this report, show an error message
  if validate_user and not (job.report.belongs_to_user(user) or user_is_admin()):
    raise ReportLookupError('You do not have access to that report.', 401)

  # If all checks passed, return the report entity
  return job


def try_submit(kind, user, data, no_cache):

  try:
    # Try creating the job
    #   DuplicateDataError -> this user has already submitted this job
    #   DataFormatError    -> there is an error in the input data
    job = get_pipeline_class(kind=kind).create(user, data, no_cache=no_cache, valid_file_extensions=TOOL_INPUT_DATA_VALID_FILE_EXTENSIONS)

    # Schedule the job, if applicable
    #   CachedDataError    -> the job already has results
    if job.is_schedulable:
      job.schedule()
      ready = False

    # If job is not schedulable, its results are immediately available, i.e. ready now
    else:
      ready = True

    return {
      'cached':    False,
      'same_user': None,
      'ready':     ready,
      'data_hash': job.report.data_hash,
      'id':        job.report.id,
    }, 200

  # Duplicate job submission from this user
  except DuplicateDataError as ex:
    job = ex.handler

    # Log the event
    logger.debug(f'(CACHE HIT) User resubmitted duplicate {kind} data: id = {job.report.id}, data hash = {job.report.data_hash}, status = {job.report["status"]}')

    # Return the matching entity
    return {
      'cached':    True,
      'same_user': True,
      'ready':     job.report.is_finished(),
      'data_hash': job.report.data_hash,
      'id':        job.report.id,
      'message':   'You have already submitted this data file. Here\'s your previously generated report.',
    }, 200

  # Duplicate job submission from another user
  except CachedDataError as ex:

    # Log the event
    logger.debug(f'(CACHE HIT) User submitted cached {kind} data: id = {job.report.id}, data hash = {job.report.data_hash}, status = {job.report["status"]}')

    # Return the matching entity
    return {
      'cached':    True,
      'same_user': False,
      'ready':     job.report.is_finished(),
      'data_hash': job.report.data_hash,
      'id':        job.report.id,
      'message':   'A matching report was found.',
    }, 200

  # Formatting error in uploaded data file
  except DataFormatError as ex:

    # Log the error
    logger.error(f'Data formatting error in {kind} file upload: {ex.msg} (Line: {ex.line or "n/a"})')

    # Construct user-friendly error message with optional line number
    msg = f'There was an error with your file. { ex.msg }'
    if ex.line is not None:
      msg += f' (Line: { ex.line })'

    # Return the error message
    return { 'message': msg }, 400

  # General error
  except Exception as ex:

    # Get message and description, if they exist
    msg  = getattr(ex, 'message',     '')
    desc = getattr(ex, 'description', '')

    # Log the full error
    logger.error(f'Error submitting {kind} calculation. Message = "{msg}", Description = "{desc}". Full Error: {ex}')

    # Return the error message
    # TODO: Update this wording
    return { 'message': "There was a problem submitting your request." }, 500
