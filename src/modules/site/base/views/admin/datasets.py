from datetime import datetime, timezone
from flask import request, render_template, Blueprint, redirect, url_for

from base.forms import DatasetReleaseForm
from base.utils.auth import jwt_required, get_jwt, admin_required

from caendr.models.datastore import DatasetRelease
from caendr.models.error import UnprocessableEntity
from caendr.services.dataset_release import get_all_dataset_releases, create_new_dataset_release, get_dataset_release, delete_dataset_release

admin_dataset_bp = Blueprint('admin_dataset',
                            __name__,
                            template_folder='templates')


@admin_dataset_bp.route('', methods=["GET"])
@admin_required()
def admin_dataset():
  alt_parent_breadcrumb = {"title": "Admin", "url": url_for('admin.admin')}
  title = 'Dataset Releases'
  datasets = get_all_dataset_releases(placeholder=False)
  return render_template('admin/dataset_list.html', **locals())


@admin_dataset_bp.route('/create', methods=["GET", "POST"])
@admin_required()
def dataset_create():
  alt_parent_breadcrumb = {"title": "Admin/Datasets", "url": url_for('admin_dataset.admin_dataset')}

  title = "Create Dataset Release"
  jwt_csrf_token = (get_jwt() or {}).get("csrf")
  form = DatasetReleaseForm(request.form)
  if request.method == 'POST' and form.validate_on_submit():
    version = request.form.get('version')
    wormbase_version = f'WS{request.form.get("wormbase_version")}'
    report_type = request.form.get('report_type')
    disabled = request.form.get('disabled') or False
    hidden = request.form.get('hidden') or False

    create_new_dataset_release(version, wormbase_version, report_type, disabled, hidden)
    return redirect(url_for("admin_dataset.admin_dataset"), code=302)

  return render_template('admin/dataset_edit.html', **locals())


@admin_dataset_bp.route('/<id>/edit', methods=["GET", "POST"])
@admin_required()
def dataset_edit(id=None):
  alt_parent_breadcrumb = {"title": "Admin/Datasets", "url": url_for('admin_dataset.admin_dataset')}
  if id is None:
    raise UnprocessableEntity('Error: No dataset release id in URL')
  
  release = get_dataset_release(id)

  title = "Edit Dataset Release"
  jwt_csrf_token = (get_jwt() or {}).get("csrf")
  form = DatasetReleaseForm(request.form, 
                            version=release.version,
                            wormbase_version=release.wormbase_version,
                            report_type=release.report_type,
                            hidden=hasattr(release, 'hidden'),
                            disabled=hasattr(release, 'disabled'))
  # TODO: add support for edit
  return render_template('admin/dataset_edit.html', **locals())


@admin_dataset_bp.route('/<id>/delete', methods=["GET"])
@admin_required()
def dataset_delete(id=None):
  if id is None:
    raise UnprocessableEntity('Error: No dataset release id in URL')
  
  release = delete_dataset_release(id)
  return redirect(url_for("admin_dataset.admin_dataset"), code=302)

