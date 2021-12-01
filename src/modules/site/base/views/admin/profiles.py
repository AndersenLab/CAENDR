from flask import Blueprint, render_template, url_for, request, redirect

from base.forms import AdminEditProfileForm
from base.utils.auth import get_jwt, admin_required

from caendr.services.profile import get_profile, get_all_profiles, create_new_profile, delete_profile, update_profile, upload_profile_photo
from caendr.models.datastore.profile import Profile


admin_profile_bp = Blueprint('admin_profile',
                            __name__,
                            template_folder='templates')


@admin_profile_bp.route('/', methods=["GET"])
@admin_profile_bp.route('/<id>', methods=["GET"])
@admin_required()
def admin_profile(id=None):
  alt_parent_breadcrumb = {"title": "Admin", "url": url_for('admin.admin')}
  if id is None:
    title = 'Profiles'
    profiles = get_all_profiles()
    return render_template('admin/profile/list.html', **locals())
  else:
    return redirect(url_for('admin_profile.profile_edit', id=id))



@admin_profile_bp.route('/create', methods=["GET", "POST"])
@admin_required()
def profile_create():
  alt_parent_breadcrumb = {"title": "Admin/Profiles", "url": url_for('admin_profile.admin_profile')}

  title = "Create Public Profile"
  jwt_csrf_token = (get_jwt() or {}).get("csrf")
  form = AdminEditProfileForm(request.form)
  if request.method == 'POST' and form.validate_on_submit():
    props = get_form_props(request)
    p = create_new_profile(**props)
    file = request.files['file']
    if file:
      upload_profile_photo(p, file)

    return redirect(url_for("admin_profile.admin_profile"), code=302)

  return render_template('admin/profile/edit.html', **locals())


@admin_profile_bp.route('/<id>/edit', methods=["GET", "POST"])
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

  return render_template('admin/profile/edit.html', **locals())


@admin_profile_bp.route('/<id>/delete', methods=["GET"])
@admin_required()
def profile_delete(id=None):
  if id is None:
    raise UnprocessableEntity('Error: No profile id in URL')
  
  release = delete_profile(id)
  return redirect(url_for("admin_profile.admin_profile"), code=302)


def get_form_props(request):
  return {
    'first_name': request.form.get('first_name'),
    'last_name': request.form.get('last_name'),
    'title': request.form.get('title'),
    'org': request.form.get('org'),
    'email': request.form.get('email'),
    'website': request.form.get('website'),
    'prof_roles': request.form.getlist('prof_roles')
  }


def populate_form_fields(request, p):
  mapping = {}
  mapping['first_name'] = p.first_name if hasattr(p, 'first_name') else ''
  mapping['last_name'] = p.last_name if hasattr(p, 'last_name') else ''
  mapping['title'] = p.title if hasattr(p, 'title') else ''
  mapping['org'] = p.org if hasattr(p, 'org') else ''
  mapping['email'] = p.email if hasattr(p, 'email') else ''
  mapping['website'] = p.website if hasattr(p, 'website') else ''
  mapping['prof_roles'] = p.prof_roles if hasattr(p, 'prof_roles') else ''
  return AdminEditProfileForm(request.form, **mapping)