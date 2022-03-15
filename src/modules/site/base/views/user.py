from flask import request, render_template, Blueprint, redirect, url_for, flash
from slugify import slugify
from datetime import datetime, timezone
from config import config

from caendr.models.datastore import User
from caendr.services.cloud.secret import get_secret
from caendr.services.user import get_user_by_email

from caendr.services.email import send_email, PASSWORD_RESET_EMAIL

from base.forms import UserRegisterForm, UserUpdateForm, RecoverUserForm, PasswordResetForm
from base.utils.auth import jwt_required, get_jwt, get_current_user, assign_access_refresh_tokens

SITE_BASE_URL = config.get('MODULE_SITE_BASE_URL', 'None')
PASSWORD_PEPPER = get_secret('PASSWORD_PEPPER')

user_bp = Blueprint('user',
                    __name__,
                    template_folder='templates')


@user_bp.route('/')
def user():
  """
      Redirect base route to the user profile page
  """
  return redirect(url_for('user.user_profile'))


@user_bp.route("/register", methods=["GET", "POST"])
def user_register():
  title = 'Register'
  form = UserRegisterForm(request.form)
  if request.method == 'POST' and form.validate():
    username = request.form.get('username')
    password = request.form.get('password')
    full_name = request.form.get('full_name')
    email = request.form.get('email')
    roles = ['user']
    id = slugify(username)
    user = User(id)
    user.set_properties(username=username, password=password, salt=PASSWORD_PEPPER, full_name=full_name, email=email, roles=roles, last_login=datetime.now(timezone.utc), provider='local')
    user.save()
    return assign_access_refresh_tokens(username, user.roles, url_for("user.user_profile"))
  return render_template('user/register.html', **locals())


@user_bp.route("/profile", methods=["GET"])
@jwt_required()
def user_profile():
  """        The User Account Profile
  """
  title = 'Profile'
  user = get_current_user()
  return render_template('user/profile.html', **locals())


@user_bp.route("/update", methods=["GET", "POST"])
@jwt_required()
def user_update():
  """        Modify The User Account Profile
  """
  title = 'Profile'
  jwt_csrf_token = (get_jwt() or {}).get("csrf")
  user = get_current_user()
  form = UserUpdateForm(request.form, full_name=user.full_name, email=user.email)
  if request.method == 'POST' and form.validate():
    email = request.form.get('email')
    full_name = request.form.get('full_name')
    password = request.form.get('password')
    user.set_properties(email=email, full_name=full_name, password=password)
    user.save()
    return redirect(url_for('user.user_profile'))
  return render_template('user/update.html', **locals())


@user_bp.route("/recover", methods=["GET", "POST"])
def recover_user():
  title = "Recover User"
  disable_parent_breadcrumb = True
  form = RecoverUserForm(request.form)
  if request.method == 'POST' and form.validate():
    email = request.form.get("email")
    users = get_user_by_email(email)
    if users[0]:
      user = users[0]
      token = "123546"
      email_obj = {}
      email_obj['base_url'] = SITE_BASE_URL
      email_obj['email'] = user.get('email')
      email_obj['token'] = token
      try:
        send_email({"from": "no-reply@elegansvariation.org",
                  "to": [user["email"]],
                  "subject": "CeNDR Password Reset",
                  "text": PASSWORD_RESET_EMAIL.format(**email_obj)})
        flash(f"We have sent an email to '{email}' containing further instructions to reset your password.", 'info')
        return redirect('/')
      except:
        flash("Failed to send email", "danger")
    
  return render_template('user/recover_user.html', **locals())


@user_bp.route("/password/reset", methods=["GET", "POST"])
def reset_password():
  title = "Reset Password"
  disable_parent_breadcrumb = True
  form = PasswordResetForm(request.form)
  token = request.args.get('token')
  print(token)
  # user = User(username)

  if request.method == 'POST' and form.validate():
    username = slugify(request.form.get("username"))
    user = User(username)
    if user._exists:
      
      flash('Password reset sent.', 'success')

    flash('Wrong username or password', 'error')
    return redirect(request.referrer)
  return render_template('user/reset_password.html', **locals())
