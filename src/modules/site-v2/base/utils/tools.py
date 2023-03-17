import os

from base.utils.auth import get_current_user, user_is_admin
from werkzeug.utils import secure_filename

from caendr.models.error import ReportLookupError, FileUploadError
from caendr.utils.data import unique_id


uploads_dir = os.path.join('./', 'uploads')
os.makedirs(uploads_dir, exist_ok=True)


def validate_report(report, user=None):

  # If no user explicitly provided, default to current user
  if user is None:
    user = get_current_user()

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


def upload_file(request, filename):
  '''
    Save uploaded file to server temporarily with unique generated name.
  '''

  # Create a unique local filename for the file
  # TODO: Is there a better way to generate this name?
  #       Using a Tempfile, using the user's ID and the time, etc.?
  local_path = os.path.join(uploads_dir, secure_filename(f'{ unique_id() }.tsv'))

  # Get the FileStorage object from the request
  file = request.files.get(filename)
  if not file:
    raise FileUploadError()

  # Save the file, alerting the user if this fails
  try:
    file.save(local_path)
  except Exception:
    raise FileUploadError()

  # Return the name of the file on the server
  return local_path
