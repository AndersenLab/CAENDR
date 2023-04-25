from flask import jsonify
from caendr.services.logger import logger
class APIError(Exception):
  """ General API Error exception handler base class """
  def default_handler(self):
    logger.error(f'ERROR: {self.description}')
    response = {"error": self.description}
    return jsonify(response), self.code

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
  """ General Error exception handler base class """
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

class CloudStorageUploadError(InternalError):
  description = "Error uploading a blob to cloud storage"

class PipelineRunError(InternalError):
  description = "Unable to start the lifesciences pipeline"
  
class JSONParseError(InternalError):
  description = "Unable to parse JSON"
  
class UnprocessableEntity(InternalError):
  description = "Unprocessable Entity"
class CachedDataError(InternalError):
  description = "This data has already been submitted by another user"

class DuplicateDataError(InternalError):
  description = "This data has already been submitted by the same user"

class DuplicateTaskError(InternalError):
  description = "This task has already been scheduled"
  
class DataFormatError(InternalError):
  description = "Error parsing data with expected format"
  def __init__(self, msg, line: int=None):
    self.msg  = msg.strip()
    self.line = line

class GoogleSheetsParseError(InternalError):
  description = "Unable to parse Google Sheets document"


class EnvLoadError(InternalError):
  def __init__(self, filename, source):
    self.filename = filename
    self.source = source
    self.description = f'Error loading environment variables from file {filename}: {self.source}'

class EnvNotLoadedError(InternalError):
  def __init__(self, var_name):
    self.description = f"Must load a .env file before trying to access environment variable {var_name}"

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

class FileUploadError(InternalError):
  description = "Could not upload file"

  def __init__(self, description=None):
    if description is not None:
      self.description = description

class SpeciesUrlNameError(InternalError):
  def __init__(self, species_name):
    self.species_name = species_name

class InvalidTokenError(InternalError):
  def __init__(self, token):
    self.token = token
    self.description = f'Invalid token name {token}'

class MissingTokenError(InternalError):
  description = 'Cannot get filled-in template until all tokens are defined'
