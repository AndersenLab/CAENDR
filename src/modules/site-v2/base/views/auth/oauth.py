from datetime import datetime, timezone

import os

from flask import (redirect,
                   url_for,
                   session,
                   flash,
                   request,
                   make_response,
                   jsonify)
from flask_dance.contrib.google import make_google_blueprint, google as google_fd
from flask_dance.consumer import oauth_authorized

from base.utils.auth import assign_access_refresh_tokens

from caendr.models.datastore import User
from caendr.models.datastore.cart import Cart
from caendr.utils.data import unique_id
from caendr.services.cloud.secret import get_secret

MODULE_SITE_CART_COOKIE_NAME = os.getenv('MODULE_SITE_CART_COOKIE_NAME')


GOOGLE_CLIENT_ID = get_secret('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = get_secret('GOOGLE_CLIENT_SECRET')
PASSWORD_PEPPER = get_secret('PASSWORD_PEPPER')

google_bp = make_google_blueprint(client_id=GOOGLE_CLIENT_ID, 
                                  client_secret=GOOGLE_CLIENT_SECRET, 
                                  scope=["https://www.googleapis.com/auth/userinfo.email",
                                          "https://www.googleapis.com/auth/userinfo.profile",
                                          "openid"],
                                  offline=True)

@google_bp.route('/')
def google():
  return redirect(url_for('auth.choose_login'))


def create_or_update_google_user(user_info):
  # Get up-to-date properties
  user_id = user_info['google']['id']
  user_email = user_info['google']['email']
  user_name = user_info['google']['name']
  user = User(user_id)
  last_login = datetime.now(timezone.utc)
  if not user._exists:
    user.roles = ['user']

  # Save updated properties
  user.set_properties(username=user_email, password=unique_id(), salt=PASSWORD_PEPPER, full_name=user_name, email=user_email.lower(), last_login=last_login, verified_email=True, user_type='OAUTH')
  user.save()
  return user


@oauth_authorized.connect
def authorized(google_bp, token):
  if not google_fd.authorized:
    flash("Error logging in!")
    return redirect(url_for("auth.choose_login"))

  user_info = google_fd.get("/oauth2/v2/userinfo")
  assert user_info.ok
  user_info = {'google': user_info.json()}
  user = create_or_update_google_user(user_info)
  resp = make_response(assign_access_refresh_tokens(user.name, user.roles, session.get("login_referrer")))
  new_resp = transfer_cart(resp, user)
  flash("Successfully logged in!", 'success')
  return new_resp


def transfer_cart(resp, user):
  # checks if a user has a local cart
  cart_id = request.cookies.get(MODULE_SITE_CART_COOKIE_NAME)
  if cart_id:
    local_cart = Cart(cart_id)
    if len(local_cart['items']) == 0:
      # delete cartID from cookies
      resp.delete_cookie(MODULE_SITE_CART_COOKIE_NAME)
      return
    
    # checks if a user has a cart in their account
    users_cart = Cart.lookup_by_user(user['email'])
    if users_cart:
      users_cart.delete_cart()
      users_cart.save()

    # assigns local cart to the user
    local_cart.transfer_to_user(user['email'])
    local_cart.save()

    resp.delete_cookie(MODULE_SITE_CART_COOKIE_NAME)
  return resp
    