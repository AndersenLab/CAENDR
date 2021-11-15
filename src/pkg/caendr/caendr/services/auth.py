import os
from functools import wraps
from flask import request

from caendr.services.cloud.secret import get_secret
from caendr.models.error import APIAuthError

API_SECRET_ID = os.environ.get('API_SECRET_ID')
API_SECRET_VERSION = os.environ.get('API_SECRET_VERSION')

def _verify_api_token(apiToken):
  API_SECRET = get_secret(API_SECRET_ID, API_SECRET_VERSION)
  if apiToken == API_SECRET:
    return True
  return False
  

def authenticate(f):
  @wraps(f)
  def __authenticate(*args, **kwargs):
    # Retrieve the authorization header from the request
    authHeader = request.headers.get("authorization")
    if authHeader == None:
      raise APIAuthError("Authorization header missing from request")

    # Compare the bearer token to the API secret in cloud secret store
    accessToken = authHeader[len("Bearer ") :]
    try:
      is_authenticated = _verify_api_token(accessToken)
    except Exception as err:
      print(err)
      raise APIAuthError("Failed to retrieve secret from store")

    # Confirm that the token is correct
    if is_authenticated == False:
      raise APIAuthError("Incorrect authorization header")
      
    return f(*args, **kwargs)
  return __authenticate
