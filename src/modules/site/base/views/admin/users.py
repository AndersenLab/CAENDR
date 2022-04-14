from logzero import logger
from datetime import datetime, timezone
from flask import request, render_template, Blueprint, redirect, url_for, flash

from base.forms import AdminEditUserForm
from base.utils.auth import get_jwt, admin_required, get_current_user

from caendr.models.datastore import User
from caendr.services.user import get_all_users, delete_user

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
