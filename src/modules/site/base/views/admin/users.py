from datetime import datetime, timezone
from flask import request, render_template, Blueprint, redirect, url_for

from base.forms import AdminEditUserForm
from base.utils.auth import jwt_required, get_jwt, admin_required

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
    users = get_all_users()
    return render_template('admin/user/list.html', **locals())
  else:
    return redirect(url_for('admin_users.users_edit'), id=id)


@admin_users_bp.route('/<id>/edit/', methods=["GET", "POST"])
@admin_required()
def users_edit(id=None):
  alt_parent_breadcrumb = {"title": "Admin/Users", "url": url_for('admin_users.admin_users')}
  if id is None:
    # todo: fix redirect
    return render_template('500.html'), 500

  title = "Edit User"
  jwt_csrf_token = (get_jwt() or {}).get("csrf")
  form = AdminEditUserForm(request.form)
  user = User(id)

  if request.method == 'GET':
    form.roles.data = user.roles if hasattr(user, 'roles') else ['user']

  if request.method == 'POST' and form.validate():
    user.roles = request.form.getlist('roles')
    user.save()
    return redirect(url_for('admin_users.admin_users'))

  # todo: fix redirect here
  return render_template('admin/user/edit.html', **locals())


@admin_users_bp.route('/<id>/delete', methods=["GET"])
@admin_required()
def users_delete(id=None):
  if id is None:
  # todo: fix redirect
    return render_template('500.html'), 500
  delete_user(id)
  return redirect(url_for('admin_users.admin_users'))
