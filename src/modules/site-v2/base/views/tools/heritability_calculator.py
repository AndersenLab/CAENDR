import re
import os
import datetime

from flask import (flash,
                   request,
                   redirect,
                   url_for,
                   jsonify,
                   render_template,
                   Blueprint,
                   abort)
from caendr.services.logger import logger
from datetime import datetime
import bleach

from base.forms import HeritabilityForm
from base.utils.auth import jwt_required, admin_required, get_jwt, get_current_user, user_is_admin
from base.utils.tools import get_upload_err_msg, lookup_report, try_submit
from constants import TOOL_INPUT_DATA_VALID_FILE_EXTENSIONS

from caendr.models.error import (
    EmptyReportDataError,
    EmptyReportResultsError,
    FileUploadError,
    ReportLookupError,
)
from caendr.models.datastore import Species, HeritabilityReport
from caendr.models.status import JobStatus
from caendr.api.strain import get_strains
from caendr.services.heritability_report import get_heritability_report, get_heritability_reports
from caendr.utils.data import unique_id, get_object_hash
from caendr.utils.env import get_env_var
from caendr.utils.local_file import LocalFile
from caendr.services.cloud.storage import get_blob, generate_blob_uri, BlobURISchema
from caendr.services.persistent_logger import PersistentLogger


MODULE_SITE_BUCKET_ASSETS_NAME = get_env_var('MODULE_SITE_BUCKET_ASSETS_NAME')
HERITABILITY_EXAMPLE_FILE      = get_env_var('HERITABILITY_EXAMPLE_FILE', as_template=True)



# ================== #
#   heritability     #
# ================== #

# Tools blueprint
heritability_calculator_bp = Blueprint(
  'heritability_calculator', __name__
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


@heritability_calculator_bp.route('')
@jwt_required()
def heritability_calculator():
  return render_template('tools/heritability_calculator/heritability-calculator.html', **{
    'title': "Heritability Calculator",
    'tool_alt_parent_breadcrumb': {"title": "Tools", "url": url_for('tools.tools')},

    'form': HeritabilityForm(),
    'hide_form': True,

    'strain_list': [],
    'species_list': Species.all(),
    'sample_data_urls': {
      species: generate_blob_uri(MODULE_SITE_BUCKET_ASSETS_NAME, HERITABILITY_EXAMPLE_FILE.get_string(SPECIES=species), schema=BlobURISchema.HTTPS)
        for species in Species.all().keys()
    },
  })


@heritability_calculator_bp.route('/create', methods=["GET"])
@jwt_required()
def create():
  """ This endpoint is used to create a heritability job. """
  title = "Heritability Calculator"
  alt_parent_breadcrumb = {"title": "Tools", "url": url_for('tools.tools')}
  jwt_csrf_token = (get_jwt() or {}).get("csrf")
  form = HeritabilityForm()
  strain_data = get_strains()
  strain_list = []
  for x in strain_data:
    strain_list.append(x.strain)

  hide_form = False
  id = unique_id()
  return render_template('tools/heritability_calculator/submit.html', **locals())


@heritability_calculator_bp.route('/all-results', methods=['GET'], endpoint='all_results')
@heritability_calculator_bp.route('/my-results',  methods=['GET'], endpoint='my_results')
@jwt_required()
def list_results():
  show_all = request.path.endswith('all-results')
  user = get_current_user()

  # Only show malformed Entities to admin users
  filter_errs = not user_is_admin()

  # Construct page
  return render_template('tools/report-list.html', **{

    # Page info
    'title': ('All' if show_all else 'My') + ' Heritability Results',
    'subtitle': 'Report List',
    'alt_parent_breadcrumb': {"title": "Tools", "url": url_for('tools.tools')},

    # Tool info
    'tool_name': 'heritability_calculator',
    'all_results': show_all,
    'button_labels': {
      'tool': 'New Calculation',
      'all':  'All User Results',
      'user': 'My Heritability Results',
    },

    # Table info
    'species_list': Species.all(),
    'items': get_heritability_reports(None if show_all else user.name, filter_errs),
    'columns': results_columns(),

    'JobStatus': JobStatus,
  })


@heritability_calculator_bp.route('/submit', methods=["POST"])
@jwt_required()
def submit():
  form = HeritabilityForm(request.form)
  user = get_current_user()

  # Validate form fields
  # Checks that species is in species list & label is not empty
  if not form.validate_on_submit():
    msg = "You must include a description of your data and a CSV file to upload."
    flash(msg, "danger")
    return jsonify({ 'message': msg }), 400

  # If user is admin, allow them to bypass cache with URL variable
  no_cache = bool(user_is_admin() and request.args.get("nocache", False))

  # Read fields from form
  label   = bleach.clean(request.form.get('label'))
  species = bleach.clean(request.form.get('species'))

  # Upload input file to server temporarily, and start the job
  try:
    with LocalFile(request.files.get('file'), valid_file_extensions=TOOL_INPUT_DATA_VALID_FILE_EXTENSIONS) as local_file:

      # Package submission data together into dict
      data = { 'label': label, 'species': species, 'file': local_file }

      # Try submitting the job & returning a JSON status message
      response, code = try_submit(HeritabilityReport.kind, user, data, no_cache)

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


@heritability_calculator_bp.route("/report/<id>/logs")
@jwt_required()
def view_logs(id):
  hr = get_heritability_report(id)    
  # get workflow bucket
  from google.cloud import storage
  storage_client = storage.Client()
  bucket_name = os.getenv('MODULE_API_PIPELINE_TASK_WORK_BUCKET_NAME', None)
  
  if bucket_name is None:
    return None
  prefix = f"{hr.data_hash}"
  # caendr-nextflow-work-bucket/938f561278fbdd4a546155f37cdaf47f/d4/ed062b62843eb156a22d303e0ce84b/google/logs

  blobs = storage_client.list_blobs(bucket_name, prefix=prefix, delimiter=None)
  filepaths = [ blob.name for blob in blobs ]
  log_filepaths = [ filepath for filepath in filepaths if "google/logs/action" in filepath or ".command" in filepath ]
  
  logs = []
  for log_filepath in log_filepaths:
    data = get_blob(bucket_name, log_filepath).download_as_string().decode('utf-8').strip()
    if data == "": 
      continue
    log = { 
      'blob_name': log_filepath, 
      'data': data
    }
    logs.append(log)

  return render_template("tools/heritability_calculator/logs.html", **locals())


@heritability_calculator_bp.route("/report/<id>", methods=['GET'])
@jwt_required()
def report(id):

  user = get_current_user()

  # Fetch requested heritability report
  # Ensures the report exists and the user has permission to view it
  try:
    job = lookup_report(HeritabilityReport.kind, id, user=user)

  # If the report lookup request is invalid, show an error message
  except ReportLookupError as ex:
    flash(ex.msg, 'danger')
    abort(ex.code)

  # Try getting & parsing the report data file and results
  # If result is None, job hasn't finished computing yet
  try:
    data, result = job.fetch()
    ready = result is not None

  # Error reading one of the report files
  except (EmptyReportDataError, EmptyReportResultsError) as ex:
    logger.error(f'Error fetching Heritability report {ex.id}: {ex.description}')
    return abort(404, description = ex.description)

  # General error
  except Exception as ex:
    logger.error(f'Error fetching Heritability report {id}: {ex}')
    return abort(400, description = 'Something went wrong')

  # No data file found
  if data is None:
    logger.error(f'Error fetching Heritability report {id}: Input data file does not exist')
    return abort(404)


  trait = data[0]['TraitName']

  # # TODO: Is this used? It looks like the error message(s) come from the entity's PipelineOperation
  # service_name = os.getenv('HERITABILITY_CONTAINER_NAME')
  # persistent_logger = PersistentLogger(service_name)
  # error = persistent_logger.get(id)

  return render_template("tools/heritability_calculator/result.html", **{
    'title': "Heritability Results",
    'subtitle': trait,
    'tool_alt_parent_breadcrumb': {"title": "Tools", "url": url_for('tools.tools')},

    'ready': ready,

    'fname': datetime.today().strftime('%Y%m%d.') + trait,

    'hr': job.report,
    'data': data,
    'result': result,
    'error': job.get_error(),

    'data_url': job.report.input_filepath(schema=BlobURISchema.HTTPS),
    'logs_url': url_for('heritability_calculator.view_logs', id = id),

    'JobStatus': JobStatus,
  })
