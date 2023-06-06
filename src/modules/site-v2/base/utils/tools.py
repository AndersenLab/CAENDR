import os

from caendr.services.logger import logger

from base.utils.auth import get_current_user, user_is_admin
from werkzeug.utils import secure_filename

from caendr.models.error import (
    CachedDataError,
    DataFormatError,
    DuplicateDataError,
    FileUploadError,
    ReportLookupError,
)
from caendr.models.task import TaskStatus
from caendr.services.tools import submit_job
from caendr.utils.data import unique_id
from caendr.services.cloud.secret import get_secret


uploads_dir = os.path.join('./', 'uploads')
os.makedirs(uploads_dir, exist_ok=True)

SUPPORT_EMAIL = get_secret('SUPPORT_EMAIL')


def lookup_report(EntityClass, reportId, user=None):

  # If no user explicitly provided, default to current user
  if user is None:
    user = get_current_user()

  # Retrieve the report entity from datastore, or None if no entity with that ID exists
  report = EntityClass.get_ds(reportId)

  # If no such report exists, show an error message
  if report is None:

    # Let admins know the report doesn't exist
    if user_is_admin():
      raise ReportLookupError('This is not a valid report URL.', 404)

    # For all other users, display a default "no access" message
    else:
      raise ReportLookupError('You do not have access to that report.', 401)

  # If the user doesn't have permission to view this report, show an error message
  if not (report.username == user.name or user_is_admin()):
    raise ReportLookupError('You do not have access to that report.', 401)

  # If all checks passed, return the report entity
  return report


def upload_file(request, filename, valid_file_extensions=None):
  '''
    Save uploaded file to server temporarily with unique generated name.
    Copies the file extension of the provided file

    Arguments:
      request: The Flask request object.
      filename (str): The name of the uploaded file in the request.
      valid_file_extensions(list(str), optional):
        A list of allowed file extensions. If filename does not have a valid extension, raises an error. If not provided, accepts any file extension.
  '''

  # Get the FileStorage object from the request
  file = request.files.get(filename)
  if not file:
    raise FileUploadError('You must include a CSV file with your data to upload. If this message persists, try refreshing the page and re-uploading your file.', 400)

  # Match the file extension by splitting on right-most '.' character
  try:
    file_ext = file.filename.rsplit('.', 1)[1]
  except:
    file_ext = None

  # Validate file extension, if file_ext and valid_file_extensions are defined
  if file_ext and valid_file_extensions and (file_ext not in valid_file_extensions):
    raise FileUploadError('You must include a CSV file with your data to upload. If this message persists, try refreshing the page and re-uploading your file.', 400)

  # Create a unique local filename for the file
  # TODO: Is there a better way to generate this name?
  #       Using a Tempfile, using the user's ID and the time, etc.?
  target_filename = unique_id() + (f'.{file_ext}' if file_ext else '')
  local_path = os.path.join(uploads_dir, secure_filename(target_filename))

  # Save the file, alerting the user if this fails
  try:
    file.save(local_path)
  except Exception:
    raise FileUploadError(f'There was a problem uploading your submission. Please try again. If this problem persists, please contact us at {SUPPORT_EMAIL}', 500)

  # Return the name of the file on the server
  return local_path


def try_submit(EntityClass, user, data, no_cache):

  # Try submitting the job
  try:
    report = submit_job(EntityClass, user, data, no_cache=no_cache)
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
    logger.debug(f'User resubmitted duplicate {EntityClass.kind} data: id = {ex.report.id}, data hash = {ex.report.data_hash}, status = {ex.report["status"]}')

    # Return the matching entity
    return {
      'cached':    True,
      'same_user': True,
      'ready':     ex.report['status'] == TaskStatus.COMPLETE,
      'data_hash': ex.report.data_hash,
      'id':        ex.report.id,
    }, 200

  # Duplicate job submission from another user
  except CachedDataError as ex:

    # Log the event
    logger.debug(f'User submitted cached {EntityClass.kind} data: id = {ex.report.id}, data hash = {ex.report.data_hash}, status = {ex.report["status"]}')

    # Return the matching entity
    return {
      'cached':    True,
      'same_user': False,
      'ready':     ex.report['status'] == TaskStatus.COMPLETE,
      'data_hash': ex.report.data_hash,
      'id':        ex.report.id,
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
