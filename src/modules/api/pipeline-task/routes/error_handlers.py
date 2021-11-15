import logging
from flask import Blueprint, jsonify
from caendr.models.error import (APIError, 
                                 APIBadRequestError, 
                                 APIAuthError, 
                                 APIDeniedError, 
                                 APINotFoundError,
                                 APIInternalError)

error_handler_bp = Blueprint('error_handler_bp', __name__)

@error_handler_bp.app_errorhandler(APIError)
def handle_exception(err):
  """ Return custom JSON error messages """
  response = {"error": err.description, "message": ""}
  if len(err.args) > 0:
    response["message"] = err.args[0]
  logging.error(f'ERROR: {err.description}: {response["message"]}')
  return jsonify(response), err.code

@error_handler_bp.app_errorhandler(APIBadRequestError.code)
def error_bad_request(error):
  """ Return default JSON error message for unhandled Bad Request """
  return APIError.default_handler(APIBadRequestError)

@error_handler_bp.app_errorhandler(APIAuthError.code)
def error_unauthorized(error):
  """ Return default JSON error message for unhandled Authentication error """
  return APIError.default_handler(APIAuthError)

@error_handler_bp.app_errorhandler(APIDeniedError.code)
def error_not_found(error):
  """ Return default JSON error message for unhandled Access Denied error """
  return APIError.default_handler(APIDeniedError)

@error_handler_bp.app_errorhandler(APINotFoundError.code)
def error_not_found(error):
  """ Return default JSON error message for unhandled Not Found error """
  return APIError.default_handler(APINotFoundError)

@error_handler_bp.app_errorhandler(APIInternalError.code)
def error_internal_server(error):
  """ Return default JSON error message for unhandled Internal Server error """
  return APIError.default_handler(APIInternalError)
