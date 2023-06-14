import os

from caendr.services.logger import logger
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
import bleach
from flask import jsonify

from base.forms import MappingForm
from base.utils.auth  import get_jwt, jwt_required, admin_required, get_current_user, user_is_admin
from base.utils.tools import lookup_report, upload_file, try_submit
from constants import TOOL_INPUT_DATA_VALID_FILE_EXTENSIONS

from caendr.services.nemascan_mapping import get_mapping, get_mappings
from caendr.services.cloud.storage import get_blob, generate_blob_url, get_blob_list, check_blob_exists
from caendr.models.datastore import SPECIES_LIST, NemascanMapping
from caendr.models.error import (
    FileUploadError,
    ReportLookupError,
)
from caendr.models.task import TaskStatus
from caendr.utils.env import get_env_var


MODULE_SITE_BUCKET_ASSETS_NAME = get_env_var('MODULE_SITE_BUCKET_ASSETS_NAME')



genetic_mapping_bp = Blueprint(
  'genetic_mapping', __name__
)



def results_columns():
  return [
    {
      'title': 'Description',
      'class': 'label',
      'field': 'label',
      'width': 0.6,
      'link_to_data': True,
    },
    {
      'title': 'Trait',
      'class': 'trait',
      'field': 'trait',
      'width': 0.4,
    },
  ]


@genetic_mapping_bp.route('', methods=['GET'])
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
    'form': MappingForm(),

    # TODO: change
    'nemascan_container_url': 'https://github.com/AndersenLab/dockerfile/tree/nemarun/nemarun',
    'nemascan_github_url':    'https://github.com/AndersenLab/NemaScan',

    # Species list
    'species_list': SPECIES_LIST,
    'species_fields': [
      'name', 'short_name', 'project_num', 'wb_ver', 'latest_release',
    ],

    # Sample data
    'sample_data_url': generate_blob_url(MODULE_SITE_BUCKET_ASSETS_NAME, 'data/nemascan_sample_data.tsv'),
  })


@genetic_mapping_bp.route('/submit', methods=['POST'])
@jwt_required()
def submit():
  form = MappingForm(request.form)
  user = get_current_user()

  # If user is admin, allow them to bypass cache with URL variable
  no_cache = bool(user_is_admin() and request.args.get("nocache", False))

  # Validate form fields
  # Checks that species is in species list & label is not empty
  if not form.validate_on_submit():
    msg = "You must include a description of your data and a CSV file to upload."
    flash(msg, "danger")
    return jsonify({ 'message': msg }), 400

  # Read fields from form
  label   = bleach.clean(request.form.get('label'))
  species = bleach.clean(request.form.get('species'))

  # Save uploaded file to server temporarily, displaying an error message if this fails
  try:
    local_path = upload_file(request, 'file', valid_file_extensions=TOOL_INPUT_DATA_VALID_FILE_EXTENSIONS)
  except FileUploadError as ex:
    flash(ex.description, 'danger')
    return jsonify({ 'message': ex.description }), ex.code

  # Package submission data together into dict
  data = {
    'label':    label,
    'species':  species,
    'filepath': local_path,
  }

  # Try submitting the job & returning a JSON status message
  try:
    response, code = try_submit(NemascanMapping, user, data, no_cache)

    # If there was an error, flash it
    if not code == 200:
      flash(response['message'], 'danger')

    elif response['message'] and response['ready']:
      flash(response['message'], 'success')

    # Return the response
    return jsonify( response ), code

  # Ensure the local file is removed, even if an error is uncaught in the submission process
  finally:
    try:
      os.remove(local_path)
    except FileNotFoundError:
      pass


@genetic_mapping_bp.route('/all-results', methods=['GET'], endpoint='all_results')
@genetic_mapping_bp.route('/my-results',  methods=['GET'], endpoint='my_results')
@jwt_required()
def list_results():
  show_all = request.path.endswith('all-results')
  user = get_current_user()

  # Only show malformed Entities to admin users
  filter_errs = not user_is_admin()

  # Construct page
  return render_template('tools/report-list.html', **{

    # Page info
    'title': ('All' if show_all else 'My') + ' Genetic Mappings',
    'alt_parent_breadcrumb': {"title": "Tools", "url": url_for('tools.tools')},

    # Tool info
    'tool_name': 'genetic_mapping',
    'all_results': show_all,
    'button_labels': {
      'tool': 'New Genetic Mapping',
      'all':  'All User Mappings',
      'user': 'My Genetic Mappings',
    },

    # Table info
    'species_list': SPECIES_LIST,
    'items': get_mappings(None if show_all else user.name, filter_errs),
    'columns': results_columns(),

    'TaskStatus': TaskStatus,
  })


@genetic_mapping_bp.route('/report/<id>', methods=['GET'])
@jwt_required()
def report(id):

  # Fetch requested mapping report
  # Ensures the report exists and the user has permission to view it
  try:
    mapping = lookup_report(NemascanMapping.kind, id)

  # If the report lookup request is invalid, show an error message
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

  # Get the trait name, if it exists
  trait = mapping['trait']

  return render_template('tools/genetic_mapping/report.html', **{

    # Page info
    'title': 'Genetic Mapping Report',
    'subtitle': mapping['label'] + (f': {trait}' if trait is not None else ''),
    'alt_parent_breadcrumb': {"title": "Tools", "url": url_for('tools.tools')},

    # Job status
    'mapping_status': mapping['status'],

    'id': id,

    # URLs
    'report_url': report_url,
    'report_status_url': url_for("genetic_mapping.report_status", id=id),
    'data_download_url': data_download_url,

    'fluid_container': True,
  })


@genetic_mapping_bp.route('/report/<id>/fullscreen', methods=['GET'])
@jwt_required()
def report_fullscreen(id):

  # Fetch requested mapping report
  # Ensures the report exists and the user has permission to view it
  try:
    mapping = lookup_report(NemascanMapping.kind, id)

  # If the report lookup request is invalid, show an error message
  except ReportLookupError as ex:
    flash(ex.msg, 'danger')
    abort(ex.code)

  # Download the report files, if they exist
  if mapping.report_path is not None:
    blob = get_blob(mapping.get_bucket_name(), mapping.report_path)
    report_contents = blob.download_as_text()
  else:
    report_contents = None

  # Return the report
  return report_contents


@genetic_mapping_bp.route('/report/<id>/status', methods=['GET'])
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


@genetic_mapping_bp.route('/report/<id>/results', methods=['GET'])
@jwt_required()
def results(id):

  # Fetch requested mapping report
  # Ensures the report exists and the user has permission to view it
  try:
    mapping = lookup_report(NemascanMapping.kind, id)

  # If the report lookup request is invalid, show an error message
  except ReportLookupError as ex:
    flash(ex.msg, 'danger')
    abort(ex.code)

  # Get the trait, if it exists
  trait = mapping['trait']

  # # Old way to compute list of blobs, that was hidden beneath 'return'
  # # Can this be deleted?
  # data_blob = RESULT_BLOB_PATH.format(data_hash=ns.data_hash)
  # blobs = list_files(data_blob)

  # Get the list of files in this report, truncating all names to everything after second-to-last '/'
  file_list = [
    {
      "name": '/'.join( blob.name.rsplit('/', 2)[1:] ),
      "url":  blob.public_url,
    }
    for blob in get_blob_list(mapping.get_bucket_name(), mapping.get_result_path())
  ]

  return render_template('tools/genetic_mapping/result_files.html', **{
    'title': 'Genetic Mapping Result Files',
    'alt_parent_breadcrumb': {"title": "Tools", "url": url_for('tools.tools')},
    'subtitle': mapping.label + (f': {trait}' if trait else ''),
    'file_list': file_list,
  })
