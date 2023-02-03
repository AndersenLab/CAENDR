from caendr.services.logger import logger
from flask import Blueprint, render_template, request, redirect, url_for, flash
import bleach
from flask import jsonify


from base.utils.auth import get_jwt, jwt_required, admin_required, get_current_user
from base.forms import FileUploadForm

from caendr.services.nemascan_mapping import create_new_mapping, get_mapping, get_all_mappings, get_user_mappings
from caendr.services.cloud.storage import get_blob, generate_blob_url, get_blob_list


genetic_mapping_bp = Blueprint(
  'genetic_mapping', __name__
)


@genetic_mapping_bp.route('/genetic-mapping/', methods=['GET'])
@jwt_required()
def genetic_mapping():
  """
      This is the mapping submission page.
  """
  title = 'Genetic Mapping'
  alt_parent_breadcrumb = {"title": "Tools", "url": url_for('tools.tools')}
  jwt_csrf_token = (get_jwt() or {}).get("csrf")
  form = FileUploadForm()
  # TODO: change
  nemascan_container_url = 'https://github.com/AndersenLab/dockerfile/tree/nemarun/nemarun'
  nemascan_github_url = 'https://github.com/AndersenLab/NemaScan'
  return render_template('tools/genetic_mapping/mapping.html', **locals())


@genetic_mapping_bp.route('/genetic-mapping/upload', methods = ['POST'])
@jwt_required()
def submit():
  form = FileUploadForm(request.form)
  user = get_current_user()
  if not form.validate_on_submit():
    flash("You must include a description of your data and a TSV file to upload", "error")
    return redirect(url_for('genetic_mapping.mapping'))
  
  label = bleach.clean(request.form.get('label'))
  props = {'label': label, 
          'username': user.name,
          'email': user.email,
          'file': request.files['file']}          
  try:
    logger.warn("Check Duplicates is DISABLED !!!")
    m = create_new_mapping(**props, check_duplicates=True)
    return redirect(url_for('genetic_mapping.report', id=m.id))
  except Exception as ex:
    if str(type(ex).__name__) == 'DuplicateDataError':
      flash('It looks like you submitted that data already - redirecting to your list of Mapping Reports', 'danger')
      return redirect(url_for('genetic_mapping.user_reports'))
    if str(type(ex).__name__) == 'CachedDataError':
      flash('It looks like that data has already been submitted - redirecting to the saved results', 'danger')
      return redirect(url_for('genetic_mapping.report', id=ex.description))
    logger.error(ex.description)
    flash(f"Unable to submit your request: \"{ex.description}\"", 'danger')
    return redirect(url_for('genetic_mapping.mapping'))

@genetic_mapping_bp.route('/genetic-mapping/reports/all', methods=['GET', 'POST'])
@admin_required()
def all_reports():
  title = 'All Genetic Mappings'
  subtitle = 'Report List'
  alt_parent_breadcrumb = {"title": "Tools", "url": url_for('tools.tools')}
  user = get_current_user()
  mappings = get_all_mappings()
  return render_template('tools/genetic_mapping/list-all.html', **locals())


@genetic_mapping_bp.route('/genetic-mapping/reports', methods=['GET', 'POST'])
@jwt_required()
def user_reports():
  title = 'My Genetic Mappings'
  subtitle = 'Report List'
  alt_parent_breadcrumb = {"title": "Tools", "url": url_for('tools.tools')}
  user = get_current_user()
  mappings = get_user_mappings(user.name)
  return render_template('tools/genetic_mapping/list-user.html', **locals())


@genetic_mapping_bp.route('/genetic-mapping/report/<id>', methods=['GET'])
@jwt_required()
def report(id):
  title = 'Genetic Mapping Report'
  alt_parent_breadcrumb = {"title": "Tools", "url": url_for('tools.tools')}
  user = get_current_user()
  mapping = get_mapping(id)
  subtitle = mapping.label +': ' + mapping.trait
  fluid_container = True
  data_url = generate_blob_url(mapping.get_bucket_name(), mapping.get_data_blob_path())
  # if hasattr(mapping, 'mapping_report_url'):
  if hasattr(mapping, 'report_path'):
    report_url = generate_blob_url(mapping.get_bucket_name(), mapping.report_path)
  else:
    report_url = None

  report_status_url = url_for("genetic_mapping.report_status", id=id)

  return render_template('tools/genetic_mapping/report.html', **locals())

@genetic_mapping_bp.route('/genetic-mapping/report/<id>/fullscreen', methods=['GET'])
@jwt_required()
def report_fullscreen(id):
  title = 'Genetic Mapping Report'
  alt_parent_breadcrumb = {"title": "Tools", "url": url_for('tools.tools')}
  user = get_current_user()
  mapping = get_mapping(id)
  subtitle = mapping.label +': ' + mapping.trait
  fluid_container = True
  data_url = generate_blob_url(mapping.get_bucket_name(), mapping.get_data_blob_path())
  # if hasattr(mapping, 'mapping_report_url'):
  if hasattr(mapping, 'report_path'):
    blob = get_blob(mapping.get_bucket_name(), mapping.report_path)
    report_contents = blob.download_as_text()
  else:
    report_contents = None

  return report_contents

@genetic_mapping_bp.route('/genetic-mapping/report/<id>/status', methods=['GET'])
@jwt_required()
def report_status(id):
  mapping = get_mapping(id)
  data_url = generate_blob_url(mapping.get_bucket_name(), mapping.get_data_blob_path())
  if hasattr(mapping, 'mapping_report_url'):
    report_url = generate_blob_url(mapping.get_bucket_name(), mapping.report_path)
  else:
    report_url = None

  payload = {
    'done': True if report_url else False,
    'report_url': report_url if report_url else "https://www.google.com"
  }
  return jsonify(payload)


@genetic_mapping_bp.route('/genetic-mapping/report/<id>/results/', methods=['GET'])
@jwt_required()
def results(id):
  title = 'Genetic Mapping Result Files'
  alt_parent_breadcrumb = {"title": "Tools", "url": url_for('tools.tools')}
  user = get_current_user()
  mapping = get_mapping(id)
  subtitle = mapping.label + ': ' + mapping.trait
  blobs = get_blob_list(mapping.get_bucket_name(), mapping.get_result_path())
  file_list = []
  for blob in blobs:
    file_list.append({
      "name": blob.name.rsplit('/', 2)[1] + '/' + blob.name.rsplit('/', 2)[2],
      "url": blob.public_url
    })
    
  return render_template('tools/genetic_mapping/result_files.html', **locals())




  data_blob = RESULT_BLOB_PATH.format(data_hash=ns.data_hash)
  blobs = list_files(data_blob)
  file_list = []
  for blob in blobs:
    file_list.append({
      "name": blob.name.rsplit('/', 2)[1] + '/' + blob.name.rsplit('/', 2)[2],
      "url": blob.public_url
    })
    
  return render_template('mapping_result_files.html', **locals())
