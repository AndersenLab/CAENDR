from flask import Blueprint, render_template, url_for, request, redirect
from logzero import logger

from base.utils.auth import admin_required, get_jwt
from base.forms import AdminEditToolContainerVersion

from caendr.services.tool_versions import get_all_containers, get_available_version_tags, get_container, get_version, update_version


admin_tools_bp = Blueprint('admin_tools',
                          __name__,
                          template_folder='templates')


@admin_tools_bp.route('/', methods=['GET'])
@admin_required()
def admin_tools():
  title = 'Tool Container Versions'
  alt_parent_breadcrumb = {"title": "Admin/Tools", "url": url_for('admin_tools.admin_tools')}
  containers = get_all_containers()

  return render_template('admin/tool/list.html', **locals())


@admin_tools_bp.route('/<id>/edit', methods=["GET", "POST"])
@admin_required()
def edit_tool(id):
  if id is None:
    raise UnprocessableEntity('Error: No profile id in URL')
  
  title = f'{id}'
  alt_parent_breadcrumb = {"title": "Admin/Tools", "url": url_for('admin_tools.admin_tools')}
  jwt_csrf_token = (get_jwt() or {}).get("csrf")
  
  tool = get_container(id)
  versions = get_available_version_tags(id)
  versions.reverse()

  form = AdminEditToolContainerVersion(version=get_version(tool))
  form.version.choices = [(ver, ver) for ver in versions] 
  if request.method == 'POST' and form.validate_on_submit():
    update_version(tool, request.form.get('version'))
    return redirect(url_for("admin_tools.admin_tools"), code=302)
    
  return render_template('admin/tool/edit.html', **locals())



'''


@admin_tools_bp.route('/<id>/edit', methods=["GET", "POST"])
@admin_required()
def profile_edit(id=None):
  alt_parent_breadcrumb = {"title": "Admin/Profiles", "url": url_for('admin_profile.admin_profile')}
  if id is None:
    raise UnprocessableEntity('Error: No profile id in URL')
  
  title = "Edit Profile"
  jwt_csrf_token = (get_jwt() or {}).get("csrf")
  p = get_profile(id)

  if request.method == 'GET':
    form = populate_form_fields(request, p)
  else: 
    form = AdminEditProfileForm(request.form)
    if request.method == 'POST' and form.validate_on_submit():
      props = get_form_props(request)
      update_profile(p, **props)
      return redirect(url_for("admin_profile.admin_profile"), code=302)

  return render_template('admin/profile/edit.html', **locals())'''