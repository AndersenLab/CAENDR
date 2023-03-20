import os

from caendr.services.logger import logger
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
import bleach
from flask import jsonify

from base.forms import FileUploadForm
from base.utils.auth  import get_jwt, jwt_required, admin_required, get_current_user, user_is_admin
from base.utils.tools import validate_report, upload_file, try_submit

from caendr.services.nemascan_mapping import create_new_mapping, get_mapping, get_all_mappings, get_user_mappings
from caendr.services.cloud.storage import get_blob, generate_blob_url, get_blob_list, check_blob_exists
from caendr.models.datastore import SPECIES_LIST, NemascanMapping
from caendr.models.error import (
    CachedDataError,
    DataFormatError,
    DuplicateDataError,
    FileUploadError,
    ReportLookupError,
)



genetic_mapping_bp = Blueprint(
  'genetic_mapping', __name__
)


@genetic_mapping_bp.route('/genetic-mapping/', methods=['GET'])
@jwt_required()
def genetic_mapping():
  """
      This is the mapping submission page.
  """
  return render_template('tools/genetic_mapping/mapping.html', **{

    # Page info
    'title': 'Genetic Mapping',
    'alt_parent_breadcrumb': {"title": "Tools", "url": url_for('tools.tools')},

    # Form info
    'jwt_csrf_token': (get_jwt() or {}).get("csrf"),
    'form': FileUploadForm(),

    # TODO: change
    'nemascan_container_url': 'https://github.com/AndersenLab/dockerfile/tree/nemarun/nemarun',
    'nemascan_github_url':    'https://github.com/AndersenLab/NemaScan',

    # Species list
    'species_list': SPECIES_LIST,
    'species_fields': [
      'name', 'short_name', 'project_num', 'wb_ver', 'latest_release',
    ],
  })


@genetic_mapping_bp.route('/genetic-mapping/upload', methods = ['POST'])
@jwt_required()
def submit():
  form = FileUploadForm(request.form)
  user = get_current_user()

  # If user is admin, allow them to bypass cache with URL variable
  no_cache = bool(user_is_admin() and request.args.get("nocache", False))

  # Validate form
  if not form.validate_on_submit():
    flash("You must include a description of your data and a TSV file to upload", "error")
    return redirect(url_for('genetic_mapping.genetic_mapping'))

  # Read fields from form
  label   = bleach.clean(request.form.get('label'))
  species = bleach.clean(request.form.get('species'))

  # Check that label is not empty
  # TODO: Move to FileUploadForm validator?
  if len(label.strip()) == 0:
    flash('Invalid label.', 'danger')
    return redirect(url_for('genetic_mapping.genetic_mapping'))

  # Check that species is valid
  # TODO: Move to FileUploadForm validator?
  if species not in SPECIES_LIST.keys():
    flash('Invalid species.', 'danger')
    return redirect(url_for('genetic_mapping.genetic_mapping'))

  # Save uploaded file to server temporarily, displaying an error message if this fails
  try:
    local_path = upload_file(request, 'file')
  except FileUploadError as ex:
    flash('There was a problem uploading your file to the server. Please try again.', 'danger')
    return redirect(url_for('genetic_mapping.genetic_mapping'))

  # Package submission data together into dict
  data = {
    'label':    label,
    'species':  species,
    'filepath': local_path,
  }

  # Try submitting the job & returning a JSON status message
  try:
    return jsonify( try_submit(NemascanMapping, user, data, no_cache) )

  # Ensure the local file is removed, even if an error is uncaught in the submission process
  finally:
    try:
      os.remove(local_path)
    except FileNotFoundError:
      pass


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

  # Get user and requested mapping
  mapping = get_mapping(id)

  # Ensure the report exists and the user has permission to view it
  try:
    validate_report(mapping)
  except ReportLookupError as ex:
    flash(ex.msg, 'danger')
    abort(ex.code)

  # Get a link to download the data, if the file exists
  if check_blob_exists(mapping.get_bucket_name(), mapping.get_data_blob_path()):
    data_download_url = generate_blob_url(mapping.get_bucket_name(), mapping.get_data_blob_path())
  else:
    data_download_url = None

  # Get a link to the report files, if they exist
  if mapping.report_path is not None:
    report_url = generate_blob_url(mapping.get_bucket_name(), mapping.report_path)
  else:
    report_url = None

  return render_template('tools/genetic_mapping/report.html', **{

    # Page info
    'title': 'Genetic Mapping Report',
    'subtitle': f'{mapping.label}: {mapping.trait}',
    'alt_parent_breadcrumb': {"title": "Tools", "url": url_for('tools.tools')},

    # Job status
    'mapping_status': mapping['status'],

    # URLs
    'report_url': report_url,
    'report_status_url': url_for("genetic_mapping.report_status", id=id),
    'data_download_url': data_download_url,

    'fluid_container': True,
  })


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
  if mapping.report_path is not None:
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

  # TODO: Definition of report_path has been changed(?) since this was written, is now a property
  #       that automatically searches for the HTML report filename. Is this the intended value here?
  #       Should this be checking mapping.report_path?
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