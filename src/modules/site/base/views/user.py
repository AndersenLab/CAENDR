from flask import request, render_template, Blueprint, redirect, url_for
from slugify import slugify
from datetime import datetime, timezone

from caendr.models.datastore import User
from caendr.services.cloud.secret import get_secret

from base.forms import UserRegisterForm, UserUpdateForm
from base.utils.auth import jwt_required, get_jwt, get_current_user, assign_access_refresh_tokens

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
