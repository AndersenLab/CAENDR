from logzero import logger
from flask import request, render_template, Blueprint, redirect, url_for, flash
from slugify import slugify
from datetime import datetime, timezone

from caendr.models.datastore import User
from caendr.services.cloud.secret import get_secret
from caendr.services.user import get_user_by_email

from caendr.services.email import send_email, PASSWORD_RESET_EMAIL

from base.forms import UserRegisterForm, UserUpdateForm, RecoverUserForm, PasswordResetForm
from base.utils.auth import jwt_required, get_jwt, get_current_user, assign_access_refresh_tokens, create_one_time_token

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
    user.set_properties(username=username, password=password, salt=PASSWORD_PEPPER, full_name=full_name, email=email, roles=roles, last_login=datetime.now(timezone.utc), user_type='LOCAL')
    user.save()
    return assign_access_refresh_tokens(username, user.roles, url_for("user.user_profile"))
  return render_template('user/register.html', **locals())


@user_bp.route("/recover", methods=["GET", "POST"])
def user_recover():
  """ Enter an email address for a user to send a password reset link """
  title = "Recover User"
  disable_parent_breadcrumb = True
  form = RecoverUserForm(request.form)

  if request.method == 'POST' and form.validate():
    email = request.form.get("email")
    users = get_user_by_email(email)

    if users and users[0]:
      user = users[0]
      token = create_one_time_token(id=user.get('username'), destination=url_for('user.user_reset_password'))
      password_reset_link = url_for('auth.token', token=token, _external=True)
      try:
        send_email({
          "from": "no-reply@elegansvariation.org",
          "to": [ email ],
          "subject": "CeNDR Password Reset",
          "text": PASSWORD_RESET_EMAIL.format(email=email, password_reset_link=password_reset_link)
        })
        logger.info(f"Sent password reset email: {email}, link: {password_reset_link}")
      except Exception as err:
        logger.error(f"Failed to send email: {err}")
    
    flash(f"We have sent an email to '{email}' containing further instructions to reset your password.", 'info')
    return redirect('/')
    
  return render_template('user/recover_user.html', **locals())


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


@user_bp.route("/password/reset", methods=["GET", "POST"])
@jwt_required()
def user_reset_password():
  title = "Reset Password"
  disable_parent_breadcrumb = True
  user = get_current_user()
  form = PasswordResetForm(request.form)

  if request.method == 'POST' and form.validate():
    password = slugify(request.form.get("password"))
    user.set_properties(password=password, salt=PASSWORD_PEPPER)
    user.save()
    flash('Password Successfully Reset.', 'success')
    return redirect(url_for('user.user_profile'))
  return render_template('user/reset_password.html', **locals())

 
