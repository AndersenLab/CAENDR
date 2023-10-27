from flask import jsonify
from caendr.services.logger import logger



class APIError(Exception):
  """
    General API Error exception handler base class
  """

  def __init__(self, message='', call_id=''):
    '''
      Args:
        - message (str, optional): A more specific description of the error.
        - call_id (str, optional): A string that helps to identify the API call that raised this error. Used for logging/debugging purposes.
    '''
    self._call_id = call_id or None
    self._message = message

  def set_call_id(self, call_id):
    self._call_id = call_id

  @property
  def message(self):
    if self._call_id:
      return f'[{self._call_id}] {self._message}'
    return self._message

  def get_response(self):
    return {
      'error':   self.description,
      'message': self.message,
    }

  def default_handler(self):
    logger.error(f'ERROR: {self.description}')
    return jsonify(self.get_response()), self.code


class APIBadRequestError(APIError):
  """ API Bad Request exception error handler """
  code = 400
  description = "Bad Request"

class APIAuthError(APIError):
  """ API Authentication exception error handler """
  code = 401
  description = "Authentication Error"

class APIDeniedError(APIError):
  code = 403
  description = "Permission Denied"

class APINotFoundError(APIError):
  code = 404
  description = "Not Found"

class APIUnprocessableEntity(APIError):
  code = 422
  description = "Unprocessable Entity"

class APIInternalError(APIError):
  code = 500
  description = "Internal Server Error"



class InternalError(Exception):
  """
    General Error exception handler base class
  """
  def __init__(self):
    super().__init__(self.description)

  def default_handler(self):
    logger.error(f'ERROR: {self.description}')
    return self.get('description', 'NO DESCRIPTION', self.code)

class BadRequestError(InternalError):
  description = "Bad Request"

class NotFoundError(InternalError):
  description = 'Not Found'
  def __init__(self, lookup_class, params):
    self.params = params

    if lookup_class:
      try:
        self.kind = lookup_class.kind
      except:
        self.kind = lookup_class
    else:
      self.kind = 'object'

    param_str = ', '.join([ f'"{key}" = "{val}"' for key, val in self.params.items() ])
    self.description = f'Could not find {self.kind} where [{param_str}].'
    super().__init__()

class CloudStorageUploadError(InternalError):
  description = "Error uploading a blob to cloud storage"

class PipelineRunError(InternalError):
  description = "Unable to start the lifesciences pipeline"
  def __init__(self, desc=None):
    if desc is not None:
      self.description = desc
    super().__init__()

class JSONParseError(InternalError):
  description = "Unable to parse JSON"
  
class UnprocessableEntity(InternalError):
  description = "Unprocessable Entity"



class CachedDataError(InternalError):
  description = "This data has already been submitted by another user"
  def __init__(self, report):
    self.report = report
    if report is not None and hasattr(report, 'data_hash'):
      self.description = f'This data (hash {getattr(report, "data_hash")}) has already been submitted by another user'
    super().__init__()

class DuplicateDataError(InternalError):
  description = "This data has already been submitted by the same user"
  def __init__(self, handler):
    self.handler = handler
    if handler is not None and hasattr(handler, 'data_hash'):
      self.description = f'This data (hash {getattr(getattr(handler, "report"), "data_hash")}) has already been submitted by the same user'
    super().__init__()

class DuplicateTaskError(InternalError):
  description = "This task has already been scheduled"



class DataFormatError(InternalError):
  description = "Error parsing data with expected format"
  def __init__(self, msg, line: int=None):
    self.msg  = msg.strip()
    self.line = line
    super().__init__()

class PreflightCheckError(InternalError):
  description = "One or more files required for this job were not found"
  def __init__(self, missing_files: list):
    self.missing_files = missing_files
    super().__init__()

class GoogleSheetsParseError(InternalError):
  description = "Unable to parse Google Sheets document"

class ExternalMarkdownRenderError(InternalError):
  def __init__(self, url, src):
    self.url = url
    self.src = src
    self.description = f'Unable to render markdown file from {url}: {src}'
    super().__init__()


class EnvLoadError(InternalError):
  def __init__(self, filename, source):
    self.filename = filename
    self.source = source
    self.description = f'Error loading environment variables from file {filename}: {self.source}'
    super().__init__()

class EnvNotLoadedError(InternalError):
  def __init__(self, var_name):
    self.description = f"Must load a .env file before trying to access environment variable {var_name}"
    super().__init__()

class EnvVarError(InternalError):
  '''
    Thrown if an environment variable is requested, but cannot be found.

    Important: This error might be thrown if trying to access *any* environment variable *before* the .env file is loaded.
      This case should normally be covered by EnvNotLoadedError, however.
  '''
  default_msg = 'is not defined. Please ensure the ".env" file defines this variable, and is loaded before trying to access it.'

  def __init__(self, var_name: str, msg: str = None):
    self.var_name = var_name

    # Construct a description message from the provided variable name and message
    self.description = f'{ EnvVarError._format_var_name(self.var_name) } {msg if msg is not None else self.default_msg}'

    super().__init__()

  @staticmethod
  def _format_var_name(var_name: str):
    if var_name:
      return 'The environment variable ' + var_name
    else:
      return 'A required environment variable'


class BasicAuthError(InternalError):
  def __init__(self, description):
    self.description = description
    super().__init__()


class NonUniqueEntity(InternalError):
  def __init__(self, kind, key, val, matches):
    self.kind = kind
    self.key  = key
    self.val  = val
    self.matches = matches
    self.description = f'Found multiple {kind} entities with field "{key}" = "{val}".'
    super().__init__()


class ReportLookupError(InternalError):
  def __init__(self, msg, code):
    self.msg = msg
    self.code = code
    self.description = msg
    super().__init__()

class EmptyReportDataError(InternalError):
  def __init__(self, report_id):
    self.id = report_id
    self.description = 'Input data file is empty'
    super().__init__()

class EmptyReportResultsError(InternalError):
  def __init__(self, report_id):
    self.id = report_id
    self.description = 'Output report file is empty'
    super().__init__()


class FileUploadError(InternalError):
  description = "Could not upload file"

  def __init__(self, description=None, code=500):
    if description is not None:
      self.description = description
      self.code = code
    super().__init__()


class SpeciesUrlNameError(InternalError):
  def __init__(self, species_name):
    self.species_name = species_name

class InvalidTokenError(InternalError):
  def __init__(self, token, source):
    self.token = token
    self.description = f'Invalid token name ${token} in {source}'
    super().__init__()

class MissingTokenError(InternalError):
  def __init__(self, token, template=None):
    self.token    = token
    self.template = template

    self.description = 'Missing value for token'
    if token:
      self.description += f' ${token}'
    if template:
      self.description += f' in template "{template}"'

    super().__init__()


class UnschedulableJobTypeError(InternalError):
  pass

class JobAlreadyScheduledError(InternalError):
  pass
