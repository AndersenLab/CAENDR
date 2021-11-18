from flask import jsonify

class APIError(Exception):
  """ General API Error exception handler base class """
  def default_handler(self):
    print(f'ERROR: {self.description}')
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
  """ API Permission Denied exception error handler """
  code = 403
  description = "Permission Denied"

class APINotFoundError(APIError):
  """ API Route not found exception error handler """
  code = 404
  description = "Not Found"

class APIUnprocessableEntity(APIError):
  """ API Unprocessable Entity error handler """
  code = 422
  description = "Unprocessable Entity"

class APIInternalError(APIError):
  """ API Internal server exception error handler """
  code = 500
  description = "Internal Server Error"

class InternalError(Exception):
  """ General Error exception handler base class """
  def default_handler(self):
    print(f'ERROR: {self.description}')
    return self.get('description', 'NO DESCRIPTION', self.code)

class BadRequestError(InternalError):
  """ Bad Request exception error handler """
  description = "Bad Request"

class CloudStorageUploadError(InternalError):
  """ Bad Request exception error handler """
description = "Error uploading a blob to cloud storage"

class JSONParseError(InternalError):
  """ Bad Request exception error handler """
  description = "Unable to parse JSON"
