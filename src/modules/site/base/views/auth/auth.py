import os
from logzero import logger


from datetime import datetime, timezone
import time
from flask import (abort,
                  redirect,
                  url_for,
                  render_template,
                  session,
                  request,
                  make_response,
                  flash,
                  jsonify,
                  Blueprint)
from slugify import slugify

from base.forms import BasicLoginForm
from base.utils.auth import (create_access_token, 
                            set_access_cookies,
                            get_jwt_identity,
                            jwt_required,
                            assign_access_refresh_tokens,
                            unset_jwt,
                            decode_token,
                            check_if_token_revoked)

from caendr.models.datastore import User
from caendr.services.cloud.secret import get_secret


PASSWORD_PEPPER = get_secret('PASSWORD_PEPPER')
auth_bp = Blueprint('auth',
                    __name__,
                    template_folder='templates')

@auth_bp.route('/')
def auth():
  return redirect(url_for('auth.choose_login'))

@auth_bp.route('/token')
def token():
  token = request.args.get('token')
  if token:
    decoded_token = decode_token(token)
    token_revoked = check_if_token_revoked(decoded_token)

    if not token_revoked:
      username = decoded_token.get('sub')
      user = User(username)
      destination = decoded_token.get('destination')
        
      if user._exists:
        user.set_properties(last_login=datetime.now(timezone.utc))
        user.save()
        flash('Logged In With Token', 'success')
        return assign_access_refresh_tokens(id=username, roles=user.roles, url=destination)
  
  return redirect(url_for('auth.choose_login'))


@auth_bp.route('/refresh', methods=['GET'])
@jwt_required(refresh=True)
def refresh():
  ''' Refreshing expired Access token '''
  username = get_jwt_identity()
  user = User(username)
  if user._exists:
    referrer = session.get('login_referrer', '/')
    return assign_access_refresh_tokens(username, user.roles, referrer, refresh=False)

  return abort(401)


@auth_bp.route("/login/select", methods=['GET'])
def choose_login(error=None):
  # Relax scope for Google
  referrer = session.get("login_referrer") or "/"
  if 'login' in referrer:
    session["login_referrer"] = '/'
  else:
    session["login_referrer"] = request.referrer
  os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = "true"
  VARS = {'page_title': 'Choose Login'}
  if error:
    flash(error, 'danger')
  return render_template('auth/select_login.html', **VARS)


@auth_bp.route("/login/basic", methods=["GET", "POST"])
def basic_login():
  title = "Login"
  logger.info(request.referrer)
  disable_parent_breadcrumb = True
  form = BasicLoginForm(request.form)
  if request.method == 'POST' and form.validate():
    username = slugify(request.form.get("username"))
    password = request.form.get("password")
    user = User(username)
    if user._exists:
      if user.check_password(password, PASSWORD_PEPPER):
        user.set_properties(last_login=datetime.now(timezone.utc))
        user.save()
        referrer = session.get('login_referrer', '/')
        if '/login/' in referrer:
          referrer = '/'
        flash('Logged In', 'success')
        return assign_access_refresh_tokens(username, user.roles, referrer)
    flash('Wrong username or password', 'error')
    return redirect(request.referrer)
  return render_template('auth/basic_login.html', **locals())


@auth_bp.route('/logout')
def logout():
  """
      Logs the user out.
  """
  session.clear()
  resp = unset_jwt()
  flash("Successfully logged out", "success")
  return resp
