import os
from caendr.services.logger import logger
from functools import wraps
from datetime import timedelta, datetime, timezone

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

PASSWORD_RESET_EXPIRATION_SECONDS = int(os.environ.get('MODULE_SITE_PASSWORD_RESET_EXPIRATION_SECONDS', '900'))


def assign_access_refresh_tokens(id, roles, url, refresh=True):
  if not url:
    url = '/'

  resp = make_response(redirect(url, 302))
  access_token = create_access_token(identity=str(id), additional_claims={'roles': roles})
  set_access_cookies(resp, access_token)

  if refresh:
    refresh_token = create_refresh_token(identity=str(id))
    set_refresh_cookies(resp, refresh_token)
  session['is_logged_in'] = True
  session['is_admin'] = ('admin' in roles)
  return resp


def create_one_time_token(id):
  expires_delta = timedelta(seconds=PASSWORD_RESET_EXPIRATION_SECONDS)
  token = create_access_token(identity=str(id), additional_claims={'type': 'password-reset'}, expires_delta=expires_delta)
  decoded_token = decode_token(token)
  jti = decoded_token['jti']
  user_token = UserToken(jti)
  user_token.set_properties(username=id, revoked=False)
  user_token.save()
  return token

def check_password_reset_token_revoked(jwt_data):
    jti = jwt_data["jti"]
    user_token = UserToken(jti)
    token_revoked = user_token.revoked
    return token_revoked


def use_password_reset_token(token):
  decoded_token = decode_token(token)
  jti = decoded_token["jti"]
  user_token = UserToken(jti)
  logger.info(f"Revoking password reset token - {jti} for user - {user_token.username}")
  user_token.revoke()
  return 


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


def user_is_admin():
  return user_has_role('admin')


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


def magic_link_required():
  def wrapper(fn):
    @wraps(fn)
    def decorator(*args, **kwargs):
      token = request.args.get('token', None) or request.form.get('password_reset_token', None)
      decoded_token = decode_token(token)

      token_revoked = check_password_reset_token_revoked(decoded_token)
      if token_revoked:
        flash("Password reset token has already been used.", "error")
        return redirect(url_for("auth.choose_login"))

      id = decoded_token.get('sub')
      user = User(id) 
      if not user._exists:
        return abort(404)

      return fn(user, *args, **kwargs)
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
  requested_route = request.path or None
  ''' Invalid auth header, redirect to login'''
  return redirect(url_for('auth.choose_login', next=requested_route)), 302
    

@jwt.invalid_token_loader
def invalid_token_callback(callback):
  ''' Invalid Fresh/Non-Fresh Access token in auth header, redirect to login '''
  logger.info("Invalid Token.")
  flash("Token is missing or invalid.", "error")
  resp = make_response(redirect(url_for('auth.choose_login')))
  session["is_logged_in"] = False
  session["is_admin"] = False
  unset_jwt_cookies(resp)
  return resp, 302


@jwt.expired_token_loader
def expired_token_callback(_jwt_header, jwt_data):
  ''' Expired auth header, redirects to fetch refresh token '''
  type = jwt_data.get('type', None)
  if type == 'password-reset':
    flash("Password reset token has expired.", "error")
    return redirect(url_for('auth.choose_login'))

  logger.info("Expired Token.")
  session['login_referrer'] = request.base_url
  resp = make_response(redirect(url_for('auth.refresh')))
  unset_access_cookies(resp)
  return resp, 302
