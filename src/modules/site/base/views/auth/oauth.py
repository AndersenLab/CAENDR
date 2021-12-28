from datetime import datetime, timezone

from flask import (redirect,
                   url_for,
                   session,
                   flash)
from flask_dance.contrib.google import make_google_blueprint, google
from flask_dance.consumer import oauth_authorized

from base.utils.auth import assign_access_refresh_tokens

from caendr.models.datastore import User
from caendr.utils.data import unique_id
from caendr.services.cloud.secret import get_secret


GOOGLE_CLIENT_ID = get_secret('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = get_secret('GOOGLE_CLIENT_SECRET')
PASSWORD_SALT = get_secret('PASSWORD_SALT')

google_bp = make_google_blueprint(client_id=GOOGLE_CLIENT_ID, 
                                  client_secret=GOOGLE_CLIENT_SECRET, 
                                  scope=["https://www.googleapis.com/auth/userinfo.profile",
                                          "https://www.googleapis.com/auth/userinfo.email",
                                          "openid"],
                                  offline=True)


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
  user.set_properties(username=user_email, password=unique_id(), salt=PASSWORD_SALT, full_name=user_name, email=user_email.lower(), last_login=last_login)
  user.verified_email = True;
  user.user_type = 'OAUTH'
  user.save()
  return user


@oauth_authorized.connect
def authorized(blueprint, token):
  if not google.authorized:
    flash("Error logging in!")
    return redirect(url_for("auth.choose_login"))

  user_info = google.get("/oauth2/v2/userinfo")
  assert user_info.ok
  user_info = {'google': user_info.json()}
  user = create_or_update_google_user(user_info)

  flash("Successfully logged in!", 'success')
  return assign_access_refresh_tokens(user.name, user.roles, session.get("login_referrer"))
