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
  
class GoogleSheetsParseError(InternalError):
  description = "Unable to parse Google Sheets document"

class EnvVarError(InternalError):
  description = "A required environment variable is not defined"
