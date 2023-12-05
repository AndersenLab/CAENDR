import os

from caendr.services.logger import logger
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
import bleach
from flask import jsonify

from base.forms import MappingForm
from base.utils.auth  import get_jwt, jwt_required, admin_required, get_current_user, user_is_admin
from base.utils.tools import get_upload_err_msg, try_submit
from base.utils.view_decorators import parse_job_id
from constants import TOOL_INPUT_DATA_VALID_FILE_EXTENSIONS

from caendr.services.nemascan_mapping import get_mapping, get_mappings
from caendr.services.cloud.storage import BlobURISchema, generate_blob_uri, get_blob, get_blob_list, check_blob_exists
from caendr.models.datastore import Species, NemascanReport
from caendr.models.error import (
    FileUploadError,
    ReportLookupError,
)
from caendr.models.job_pipeline import NemascanPipeline
from caendr.models.status import JobStatus
from caendr.utils.env import get_env_var
from caendr.utils.local_files import LocalUploadFile


MODULE_SITE_BUCKET_ASSETS_NAME = get_env_var('MODULE_SITE_BUCKET_ASSETS_NAME')
NEMASCAN_EXAMPLE_FILE          = get_env_var('NEMASCAN_EXAMPLE_FILE', as_template=True)



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
    'tool_alt_parent_breadcrumb': {"title": "Tools", "url": url_for('tools.tools')},

    # Form info
    'jwt_csrf_token': (get_jwt() or {}).get("csrf"),
    'form': MappingForm(),

    # TODO: change
    'nemascan_container_url': 'https://github.com/AndersenLab/dockerfile/tree/nemarun/nemarun',
    'nemascan_github_url':    'https://github.com/AndersenLab/NemaScan',

    # Species list
    'species_list': Species.all(),
    'species_fields': [
      'name', 'short_name', 'project_num', 'wb_ver', 'release_latest',
    ],

    # Sample data
    'sample_data_urls': {
      species: generate_blob_uri(MODULE_SITE_BUCKET_ASSETS_NAME, NEMASCAN_EXAMPLE_FILE.get_string(SPECIES=species), schema=BlobURISchema.HTTPS)
        for species in Species.all().keys()
    },
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

  # Upload input file to server temporarily, and start the job
  try:
    with LocalUploadFile(request.files.get('file'), valid_file_extensions=TOOL_INPUT_DATA_VALID_FILE_EXTENSIONS) as file:

      # Package submission data together into dict
      data = { 'label': label, 'species': species, 'file': file }

      # Try submitting the job & returning a JSON status message
      response, code = try_submit(NemascanReport.kind, user, data, no_cache)

      # If there was an error, flash it
      if code != 200 and int(request.args.get('reloadonerror', 1)):
        flash(response['message'], 'danger')

      # If the response contains a caching message, flash it
      elif response.get('message') and response.get('ready', False):
        flash(response.get('message'), 'success')

      # Return the response
      return jsonify( response ), code

  # If the file upload failed, display an error message
  except FileUploadError as ex:
    message = get_upload_err_msg(ex.code)
    flash(message, 'danger')
    return jsonify({ 'message': message }), ex.code


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
    'tool_alt_parent_breadcrumb': {"title": "Tools", "url": url_for('tools.tools')},

    # Tool info
    'tool_name': 'genetic_mapping',
    'all_results': show_all,
    'button_labels': {
      'tool': 'New Genetic Mapping',
      'all':  'All User Mappings',
      'user': 'My Genetic Mappings',
    },

    # Table info
    'species_list': Species.all(),
    'items': get_mappings(None if show_all else user.name, filter_errs),
    'columns': results_columns(),

    'JobStatus': JobStatus,
  })


@genetic_mapping_bp.route('/report/<report_id>', methods=['GET'])
@jwt_required()
@parse_job_id(NemascanPipeline, fetch=False)
def report(job: NemascanPipeline):

  # Get the trait name, if it exists
  trait = job.report['trait']

  return render_template('tools/genetic_mapping/report.html', **{

    # Page info
    'title': 'Genetic Mapping Report',
    'subtitle': job.report['label'] + (f': {trait}' if trait is not None else ''),
    'tool_alt_parent_breadcrumb': {"title": "Tools", "url": url_for('tools.tools')},

    # Job status
    'mapping_status': job.report['status'],

    'report_id': job.report.id,

    # Links to the input data file and report output files, if they exist
    'data_download_url': job.report.input_filepath(  schema = BlobURISchema.HTTPS, check_if_exists = True ),
    'report_url':        job.report.output_filepath( schema = BlobURISchema.HTTPS, check_if_exists = True ),

    'fluid_container': True,
  })


@genetic_mapping_bp.route('/report/<report_id>/fullscreen', methods=['GET'])
@jwt_required()
@parse_job_id(NemascanPipeline, fetch=False)
def report_fullscreen(job: NemascanPipeline):

  # Download the report files, if they exist
  report_contents = job.fetch_output()

  # If report could not be found, return 404 error
  if report_contents is None:
    abort(404)

  # Return the report
  return report_contents


@genetic_mapping_bp.route('/report/<id>/status', methods=['GET'])
@jwt_required()
def report_status(id):
  mapping = get_mapping(id)
  data_url = generate_blob_uri(mapping.get_bucket_name(), mapping.get_data_blob_path(), schema=BlobURISchema.HTTPS)

  # TODO: Definition of report_path has been changed(?) since this was written, is now a property
  #       that automatically searches for the HTML report filename. Is this the intended value here?
  #       Should this be checking mapping.report_path?
  if hasattr(mapping, 'mapping_report_url'):
    report_url = generate_blob_uri(mapping.get_bucket_name(), mapping.report_path, schema=BlobURISchema.HTTPS)
  else:
    report_url = None

  payload = {
    'done': True if report_url else False,
    'report_url': report_url if report_url else "https://www.google.com"
  }
  return jsonify(payload)


@genetic_mapping_bp.route('/report/<report_id>/results', methods=['GET'])
@jwt_required()
@parse_job_id(NemascanPipeline, fetch=False)
def results(job: NemascanPipeline):

  # Get the trait, if it exists
  trait = job.report['trait']

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
    for blob in job.report.list_output_blobs()
  ]

  return render_template('tools/genetic_mapping/result_files.html', **{
    'title': 'Genetic Mapping Result Files',
    'tool_alt_parent_breadcrumb': {"title": "Tools", "url": url_for('tools.tools')},
    'subtitle': job.report['label'] + (f': {trait}' if trait else ''),
    'file_list': file_list,
  })
