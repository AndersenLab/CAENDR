from caendr.services.logger import logger
from flask import Blueprint, jsonify
from caendr.models.error import (APIError, 
                                 APIBadRequestError, 
                                 APIAuthError, 
                                 APIDeniedError, 
                                 APINotFoundError,
                                 APIInternalError)

api_error_handler_bp = Blueprint('error_handler_bp', __name__)


@api_error_handler_bp.app_errorhandler(APIError)
def handle_exception(err):
  """
    Return custom JSON error messages
  """
  message = f'ERROR: {err.description}: {err.message}.'
  if err.__cause__ is not None:
    message += f' Caused by {type(err.__cause__).__name__}: {err.__cause__}'
  logger.error(message)

  return jsonify(err.get_response()), err.code


@api_error_handler_bp.app_errorhandler(APIBadRequestError.code)
def error_bad_request(error):
  """ Return default JSON error message for unhandled Bad Request """
  return APIError.default_handler(APIBadRequestError)

@api_error_handler_bp.app_errorhandler(APIAuthError.code)
def error_unauthorized(error):
  """ Return default JSON error message for unhandled Authentication error """
  return APIError.default_handler(APIAuthError)

@api_error_handler_bp.app_errorhandler(APIDeniedError.code)
def error_not_found(error):
  """ Return default JSON error message for unhandled Access Denied error """
  return APIError.default_handler(APIDeniedError)

@api_error_handler_bp.app_errorhandler(APINotFoundError.code)
def error_not_found(error):
  """ Return default JSON error message for unhandled Not Found error """
  return APIError.default_handler(APINotFoundError)

@api_error_handler_bp.app_errorhandler(APIInternalError.code)
def error_internal_server(error):
  """ Return default JSON error message for unhandled Internal Server error """
  return APIError.default_handler(APIInternalError)
