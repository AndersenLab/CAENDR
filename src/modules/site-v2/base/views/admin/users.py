from caendr.services.logger import logger
from flask import request, render_template, Blueprint, redirect, url_for, flash

from base.forms import AdminEditUserForm
from base.utils.auth import get_jwt, create_one_time_token, admin_required, get_current_user

from caendr.models.datastore import User
from caendr.services.user import get_all_users, delete_user
from caendr.services.email import send_email, PASSWORD_RESET_EMAIL_TEMPLATE

admin_users_bp = Blueprint('admin_users',
                            __name__,
                            template_folder='templates')


@admin_users_bp.route('/', methods=["GET"])
@admin_users_bp.route('/<id>', methods=["GET"])
@admin_required()
def admin_users(id=None):
  alt_parent_breadcrumb = {"title": "Admin", "url": url_for('admin.admin')}
  if id is None:
    title = 'Users'
    user_entities = get_all_users()
    users = [User(u) for u in user_entities]
    return render_template('admin/user/list.html', **locals())
  else:
    return redirect(url_for('admin_users.users_edit'), id=id)


@admin_users_bp.route('/<id>/edit/', methods=["GET", "POST"])
@admin_required()
def users_edit(id=None):
  title = "Edit User"
  jwt_csrf_token = (get_jwt() or {}).get("csrf")
  form = AdminEditUserForm(request.form)
  alt_parent_breadcrumb = {"title": "Admin/Users", "url": url_for('admin_users.admin_users')}

  user = User(id)
  if not user._exists:
    flash(f"Please select a valid user to edit", "error")
    return redirect(url_for('admin_users.admin_users'))

  if not (request.method == 'POST' and form.validate()):
    form.roles.data = user.roles if hasattr(user, 'roles') else ['user']
    return render_template('admin/user/edit.html', **locals())
  
  email = request.form.get('email')
  full_name = request.form.get('full_name')
  user.roles = request.form.getlist('roles')
  user.set_properties(email=email, full_name=full_name)
  user.save()
  flash(f"Updated user: {id}", "success")
  return redirect(url_for('admin_users.admin_users'))


@admin_users_bp.route('/<id>/recover', methods=["GET"])
@admin_required()
def users_recover(id=None):
  """ Send a password reset link to the chosen user """
  title = "Edit User"
  jwt_csrf_token = (get_jwt() or {}).get("csrf")
  alt_parent_breadcrumb = {"title": "Admin/Users", "url": url_for('admin_users.admin_users')}

  user = User(id)
  if not (user._exists or user.user_type == 'LOCAL'): 
    flash(f"Please select a valid LOCAL user to recover", "error")
    return redirect(url_for('admin_users.users_edit', id=user.name))

  email = user.email
  token = create_one_time_token(id=user.name)
  password_reset_magic_link = url_for('user.user_reset_password', token=token, _external=True)
  try:
    send_email({
      "from": "no-reply@elegansvariation.org",
      "to": [ email ],
      "subject": "CaeNDR Password Reset",
      "text": PASSWORD_RESET_EMAIL_TEMPLATE.format(email=email, password_reset_magic_link=password_reset_magic_link)
    })
    logger.info(f"Sent password reset email: {email} to user: {user.name}, link: {password_reset_magic_link}")
    flash(f"Sent password reset email to {user.full_name} ({user.name}) at {email}", "success")
  except Exception as err:
    logger.error(f"Failed to send email: {err}")
    flash(f"Unable to reset credentials for {user.name} at this time. Please try again later.", "error")
  
  return redirect(url_for('admin_users.users_edit', id=user.name))


@admin_users_bp.route('/<id>/delete', methods=["GET"])
@admin_required()
def users_delete(id=None):
  user = get_current_user()
  
  target_user = User(id)
  if id == user.name or not target_user._exists:
    flash(f"Please select a valid user to delete", "error")
    return redirect(url_for('admin_users.admin_users'))
  
  try:
    delete_user(id)
    logger.info(f"Deleting user: {id}")
    flash(f"Deleted user: {id}", "success")
  except Exception as err:
    logger.error(err)
    flash(f"Unable to delete user at this time.", "error")
  return redirect(url_for('admin_users.admin_users'))
