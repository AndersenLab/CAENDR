from logzero import logger
from functools import wraps
from datetime import timedelta
from constants import JWT_LIMITED_TOKEN_EXPIRES

from flask import (request,
                  redirect,
                  flash,
                  abort,
                  url_for,
                  session,
                  make_response)
from flask_jwt_extended import (create_access_token, 
                                create_refresh_token, 
                                set_access_cookies,
                                set_refresh_cookies,
                                unset_jwt_cookies,
                                unset_access_cookies,
                                get_jwt,
                                get_jwt_identity,
                                get_current_user,
                                verify_jwt_in_request,
                                jwt_required,
                                decode_token)

from caendr.models.datastore import User
from caendr.models.datastore.user_token import UserToken
from extensions import jwt

def create_one_time_token(id, destination='/'):
  expires_delta = timedelta(seconds=JWT_LIMITED_TOKEN_EXPIRES)
  token = create_access_token(identity=str(id), additional_claims={'destination': destination}, expires_delta=expires_delta)
  decoded_token = decode_token(token)
  jti = decoded_token['jti']
  user_token = UserToken(jti)
  user_token.set_properties(username=id, revoked=False)
  user_token.save()
  return token

def assign_access_refresh_tokens(id, roles, url, refresh=True):
  resp = make_response(redirect(url, 302))
  access_token = create_access_token(identity=str(id), additional_claims={'roles': roles})
  set_access_cookies(resp, access_token)
  if refresh:
    refresh_token = create_refresh_token(identity=str(id))
    set_refresh_cookies(resp, refresh_token)
  session['is_logged_in'] = True
  session['is_admin'] = ('admin' in roles)
  return resp


def unset_jwt():
  resp = make_response(redirect('/', 302))
  session["is_logged_in"] = False
  session["is_admin"] = False
  unset_jwt_cookies(resp)
  return resp


def user_has_role(role):
  try: 
    verify_jwt_in_request(optional=True)
    claims = get_jwt()
    return claims["roles"] and (role in claims["roles"])
  except Exception as e:
    return False

def admin_required():
  def wrapper(fn):
    @wraps(fn)
    def decorator(*args, **kwargs):
      verify_jwt_in_request()
      claims = get_jwt()
      if claims["roles"] and ('admin' in claims["roles"]):
        return fn(*args, **kwargs)
      else:
        return abort(401)

    return decorator
  return wrapper


@jwt.user_identity_loader
def user_identity_lookup(sub):
  return sub


@jwt.user_lookup_loader
def user_lookup_callback(_jwt_header, jwt_data):
  id = jwt_data["sub"]
  return User(id)


@jwt.unauthorized_loader
def unauthorized_callback(reason):
  ''' Invalid auth header, redirect to login'''
  return redirect(url_for('auth.choose_login')), 302


def check_if_token_revoked(jwt_data):
    jti = jwt_data["jti"]
    user_token = UserToken(jti)
    token_revoked = user_token.revoked
    if token_revoked:
      logger.info("Token has been revoked.")
      return make_response(redirect(url_for('auth.choose_login'))), 302
    logger.info(f"Revoking user token - {jti} for user - {user_token.username}")
    user_token.revoke()
    return token_revoked
    

@jwt.invalid_token_loader
def invalid_token_callback(callback):
  ''' Invalid Fresh/Non-Fresh Access token in auth header, redirect to login '''
  logger.info("Invalid Token.")
  resp = make_response(redirect(url_for('auth.choose_login')))
  session["is_logged_in"] = False
  session["is_admin"] = False
  unset_jwt_cookies(resp)
  return resp, 302


@jwt.expired_token_loader
def expired_token_callback(_jwt_header, jwt_data):
  ''' Expired auth header, redirects to fetch refresh token '''
  logger.info("Expired Token.")
  session['login_referrer'] = request.base_url
  resp = make_response(redirect(url_for('auth.refresh')))
  unset_access_cookies(resp)
  return resp, 302
