import os

from caendr.services.logger import logger

from base.utils.auth import get_current_user, user_is_admin

from caendr.models.datastore import IndelPrimer, NemascanMapping, HeritabilityReport
from constants import TOOL_INPUT_DATA_VALID_FILE_EXTENSIONS

from caendr.models.error import (
    CachedDataError,
    DataFormatError,
    DuplicateDataError,
    ReportLookupError,
)
from caendr.services.tools import submit_job
from caendr.services.cloud.secret import get_secret



SUPPORT_EMAIL = get_secret('SUPPORT_EMAIL')


def get_class_from_kind(kind):
  for c in [ IndelPrimer, NemascanMapping, HeritabilityReport ]:
    if kind == c.kind:
      return c


def get_upload_err_msg(code):
  CODE_TO_MSG = {
    400: 'You must include a CSV file with your data to upload. If this message persists, try refreshing the page and re-uploading your file.',
    500: f'There was a problem uploading your submission. Please try again. If this problem persists, please contact us at {SUPPORT_EMAIL}',
  }
  return CODE_TO_MSG.get(code, CODE_TO_MSG[500])


def lookup_report(kind, reportId, user=None, validate_user=True):

  # If no user explicitly provided, default to current user
  if validate_user and user is None:
    user = get_current_user()

  # Get & validate the entity class from the provided kind
  EntityClass = get_class_from_kind(kind)
  if EntityClass is None:
    if user_is_admin() or not validate_user:
      raise ReportLookupError('Invalid report type.', 400)
    else:
      raise ReportLookupError('You do not have access to that report.', 401)

  # Retrieve the report entity from datastore, or None if no entity with that ID exists
  report = EntityClass.get_ds(reportId)

  # If no such report exists, show an error message
  if report is None:

    # Let admins know the report doesn't exist
    if user_is_admin() or not validate_user:
      raise ReportLookupError('This is not a valid report URL.', 404)

    # For all other users, display a default "no access" message
    else:
      raise ReportLookupError('You do not have access to that report.', 401)

  # If the user doesn't have permission to view this report, show an error message
  if validate_user and not (report.username == user.name or user_is_admin()):
    raise ReportLookupError('You do not have access to that report.', 401)

  # If all checks passed, return the report entity
  return report


def try_submit(EntityClass, user, data, no_cache):

  # Try submitting the job
  try:
    report = submit_job(EntityClass, user, data, no_cache=no_cache, valid_file_extensions=TOOL_INPUT_DATA_VALID_FILE_EXTENSIONS)
    return {
      'cached':    False,
      'same_user': None,
      'ready':     False,
      'data_hash': report.data_hash,
      'id':        report.id,
    }, 200

  # Duplicate job submission from this user
  except DuplicateDataError as ex:

    # Log the event
    logger.debug(f'(CACHE HIT) User resubmitted duplicate {EntityClass.kind} data: id = {ex.report.id}, data hash = {ex.report.data_hash}, status = {ex.report["status"]}')

    # Return the matching entity
    return {
      'cached':    True,
      'same_user': True,
      'ready':     ex.report.is_finished(),
      'data_hash': ex.report.data_hash,
      'id':        ex.report.id,
      'message':   'You have already submitted this data file. Here\'s your previously generated report.',
    }, 200

  # Duplicate job submission from another user
  except CachedDataError as ex:

    # Log the event
    logger.debug(f'(CACHE HIT) User submitted cached {EntityClass.kind} data: id = {ex.report.id}, data hash = {ex.report.data_hash}, status = {ex.report["status"]}')

    # Return the matching entity
    return {
      'cached':    True,
      'same_user': False,
      'ready':     ex.report.is_finished(),
      'data_hash': ex.report.data_hash,
      'id':        ex.report.id,
      'message':   'A matching report was found.',
    }, 200

  # Formatting error in uploaded data file
  except DataFormatError as ex:

    # Log the error
    logger.error(f'Data formatting error in {EntityClass.kind} file upload: {ex.msg} (Line: {ex.line or "n/a"})')

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
    logger.error(f'Error submitting {EntityClass.kind} calculation. Message = "{msg}", Description = "{desc}". Full Error: {ex}')

    # Return the error message
    # TODO: Update this wording
    return { 'message': "There was a problem submitting your request." }, 500
