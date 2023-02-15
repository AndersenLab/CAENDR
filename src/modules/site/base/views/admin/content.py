from flask import Blueprint, render_template, url_for, request
from base.utils.auth import get_jwt, admin_required
from base.forms import MarkdownForm
from caendr.services.markdown import get_all_markdown_content

admin_content_bp = Blueprint('admin_content',
                            __name__)


@admin_content_bp.route('', methods=["GET"])
@admin_required()
def admin_content():
  alt_parent_breadcrumb = {"title": "Admin", "url": url_for('admin.admin')}
  title = 'Page Content'
  markdown = get_all_markdown_content()
  return render_template('admin/content/list.html', **locals())


@admin_content_bp.route('/md/create', methods=["GET", "POST"])
@admin_required()
def markdown_create():
  alt_parent_breadcrumb = {"title": "Admin/Content", "url": url_for('admin_content.admin_content')}

  title = "Create Markdown Content"
  jwt_csrf_token = (get_jwt() or {}).get("csrf")
  form = MarkdownForm(request.form)
  if request.method == 'POST' and form.validate_on_submit():
    title = request.form.get('title')
    type = request.form.get('type')

    pass
  return render_template('admin/content/edit.html', **locals())

  '''form = DatasetReleaseForm(request.form)
  if request.method == 'POST' and form.validate_on_submit():
    version = request.form.get('version')
    wormbase_version = f'WS{request.form.get("wormbase_version")}'
    report_type = request.form.get('report_type')
    disabled = request.form.get('disabled') or False
    hidden = request.form.get('hidden') or False

    create_new_dataset_release(version, wormbase_version, report_type, disabled, hidden)
    return redirect(url_for("admin_dataset.admin_dataset"), code=302)

  return render_template('admin/dataset/edit.html', **locals())'''
