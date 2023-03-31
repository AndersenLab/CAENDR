import re
import os
import datetime
from caendr.models.datastore.pipeline_operation import PipelineOperation

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
from base.utils.tools import lookup_report, upload_file, try_submit

from caendr.models.error import (
    CachedDataError,
    DataFormatError,
    DuplicateDataError,
    EmptyReportDataError,
    EmptyReportResultsError,
    FileUploadError,
    ReportLookupError,
    UnfinishedReportError,
)
from caendr.models.datastore import SPECIES_LIST, HeritabilityReport
from caendr.api.strain import get_strains
from caendr.services.heritability_report import get_all_heritability_results, get_user_heritability_results, create_new_heritability_report, get_heritability_report, fetch_heritability_report
from caendr.utils.data import unique_id, convert_data_table_to_tsv, get_object_hash
from caendr.services.cloud.storage import get_blob, generate_blob_url
from caendr.services.persistent_logger import PersistentLogger



# ================== #
#   heritability     #
# ================== #

# Tools blueprint
heritability_calculator_bp = Blueprint(
  'heritability_calculator', __name__
)


@heritability_calculator_bp.route('/heritability-calculator')
def heritability_calculator():
  title = "Heritability Calculator"
  alt_parent_breadcrumb = {"title": "Tools", "url": url_for('tools.tools')}
  form = HeritabilityForm()
  hide_form = True
  strain_list = []
  species_list = SPECIES_LIST
  return render_template('tools/heritability_calculator/heritability-calculator.html', **locals())


@heritability_calculator_bp.route('/heritability-calculator/create', methods=["GET"])
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


@heritability_calculator_bp.route("/heritability-calculator/all-results")
@admin_required()
def all_results():
  return render_template('tools/heritability_calculator/list-all.html', **{
    'title': "All Heritability Results",
    'alt_parent_breadcrumb': {"title": "Tools", "url": url_for('tools.tools')},
    'items': get_all_heritability_results(),
  })


@heritability_calculator_bp.route("/heritability-calculator/my-results")
@jwt_required()
def user_results():
  user = get_current_user()
  return render_template('tools/heritability_calculator/list-user.html', **{
    'title': "My Heritability Results",
    'alt_parent_breadcrumb': {"title": "Tools", "url": url_for('tools.tools')},
    'items': get_user_heritability_results(user.name),
  })


@heritability_calculator_bp.route('/heritability-calculator/submit', methods=["POST"])
@jwt_required()
def submit():
  form = HeritabilityForm(request.form)
  user = get_current_user()

  # TODO: Validate form
  if not form.validate_on_submit():
    pass
    # flash("You must include a description of your data and a TSV file to upload", "error")
    # return redirect(url_for('heritability_calculator.submit'))

  # If user is admin, allow them to bypass cache with URL variable
  no_cache = bool(user_is_admin() and request.args.get("nocache", False))

  # Read fields from form
  label   = bleach.clean(request.form.get('label'))
  species = bleach.clean(request.form.get('species'))

  # Check that label is not empty
  # TODO: Move to HeritabilityForm validator?
  if len(label.strip()) == 0:
    flash('Invalid label.', 'danger')
    return jsonify({
      'error': True, 'message': f"There was a problem submitting your request.",
    })

  # Check that species is valid
  # TODO: Move to HeritabilityForm validator?
  if species not in SPECIES_LIST.keys():
    flash('Invalid species.', 'danger')
    return jsonify({
      'error': True, 'message': f"There was a problem submitting your request.",
    })

  # Save uploaded file to server temporarily, displaying an error message if this fails
  try:
    local_path = upload_file(request, 'file')
  except FileUploadError as ex:
    flash('There was a problem uploading your file to the server. Please try again.', 'danger')
    return jsonify({
      'error':   True,
      'message': f"There was a problem submitting your request.",
    })

  # Package submission data together into dict
  data = {
    'label':    label,
    'species':  species,
    'filepath': local_path,
  }

  # Try submitting the job & returning a JSON status message
  try:
    response = try_submit(HeritabilityReport, user, data, no_cache)

    # If there was an error, flash it
    if not response['succeeded']:
      flash(response['message'], 'danger')

    # Return the response
    return jsonify( response )

  # Ensure the local file is removed, even if an error is uncaught in the submission process
  finally:
    try:
      os.remove(local_path)
    except FileNotFoundError:
      pass


@heritability_calculator_bp.route("/heritability-calculator/h2/<id>/logs")
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


@heritability_calculator_bp.route("/heritability-calculator/h2/<id>")
@jwt_required()
def report(id):

  user = get_current_user()

  # Fetch requested heritability report
  # Ensures the report exists and the user has permission to view it
  try:
    hr = lookup_report(HeritabilityReport, id, user=user)

  # If the report lookup request is invalid, show an error message
  except ReportLookupError as ex:
    flash(ex.msg, 'danger')
    abort(ex.code)

  # TODO: Is this used?
  data_hash = hr.data_hash

  # Try getting & parsing the report data file and results
  try:
    data, result = fetch_heritability_report(hr)
    ready = True

  # If report hasn't finished computing yet, display a waiting page
  except UnfinishedReportError:
    data, result = ex.data, None
    ready = False

  # If no submission exists, return 404
  except EmptyReportDataError:
    return abort(404, description="Heritability report not found")

  trait = data[0]['TraitName']

  # If result exists, mark as complete
  # TODO: Is this the right place for this?
  if result:
    hr.status = 'COMPLETE'
    hr.save()

  # TODO: Are either of these values used?
  format = '%I:%M %p %m/%d/%Y'
  now = datetime.now().strftime(format)

  # TODO: Is this used? It looks like the error message(s) come from the entity's PipelineOperation
  service_name = os.getenv('HERITABILITY_CONTAINER_NAME')
  persistent_logger = PersistentLogger(service_name)
  error = persistent_logger.get(id)

  return render_template("tools/heritability_calculator/result.html", **{
    'title': "Heritability Results",
    'subtitle': trait,
    'alt_parent_breadcrumb': {"title": "Tools", "url": url_for('tools.tools')},

    'ready': ready,

    # TODO: The HTML file expects a variable called "fnam" -- is that a typo?
    'fname': datetime.today().strftime('%Y%m%d.') + trait,

    'hr': hr,
    'data': data,
    'result': result,

    'data_hash': data_hash,
    'operation': hr.get_pipeline_operation(),
    'error': error,

    'data_url': generate_blob_url(hr.get_bucket_name(), hr.get_data_blob_path()),
    'logs_url': url_for('heritability_calculator.view_logs', id = id),
  })
