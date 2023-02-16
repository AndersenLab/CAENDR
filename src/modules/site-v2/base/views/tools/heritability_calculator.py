import io
import re
import os
import pandas as pd
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

from base.forms import HeritabilityForm
from base.utils.auth import jwt_required, admin_required, get_jwt, get_current_user, user_is_admin

from caendr.models.error import CachedDataError, DuplicateDataError
from caendr.models.species import SPECIES_LIST
from caendr.api.strain import get_strains
from caendr.services.heritability_report import get_all_heritability_results, get_user_heritability_results, create_new_heritability_report, get_heritability_report
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
  title = "All Heritability Results"
  alt_parent_breadcrumb = {"title": "Tools", "url": url_for('tools.tools')}
  user = get_current_user()
  items = get_all_heritability_results()
  return render_template('tools/heritability_calculator/list-all.html', **locals())


@heritability_calculator_bp.route("/heritability-calculator/my-results")
@jwt_required()
def user_results():
  title = "My Heritability Results"
  alt_parent_breadcrumb = {"title": "Tools", "url": url_for('tools.tools')}
  user = get_current_user()
  items = get_user_heritability_results(user.name)
  return render_template('tools/heritability_calculator/list-user.html', **locals())


@heritability_calculator_bp.route('/heritability-calculator/submit', methods=["POST"])
@jwt_required()
def submit_h2():
  user = get_current_user()

  # Package data for this submission into an object
  data = {
    'label':      request.values['label'],
    'table_data': request.values['table_data'],
  }

  # If user is admin, allow them to bypass cache with URL variable
  no_cache = bool(user_is_admin() and request.args.get("nocache", False))

  try:
    h = create_new_heritability_report(user, data, no_cache = False)
    return jsonify({
      'started':   True,
      'data_hash': h.data_hash,
      'id':        h.id,
    })

  except DuplicateDataError as ex:
    flash('Oops! It looks like you submitted that data already - redirecting to your list of Heritability Reports', 'danger')
    return jsonify({
      'duplicate': True,
      'data_hash': ex.args[0].data_hash,
      'id':        ex.args[0].id,
    })

  except CachedDataError as ex:
    flash('Oops! It looks like that data has already been submitted - redirecting to the saved results', 'danger')
    return jsonify({
      'cached':    True,
      'data_hash': ex.args[0].data_hash,
      'id':        ex.args[0].id,
    })

  except Exception as ex:
    flash(f"Oops! There was a problem submitting your request: {ex}", 'danger')
    return jsonify({
      'duplicate': True,
      'data_hash': None,
      'id':        None,
    })


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

# TODO: Move this into a separate service
@heritability_calculator_bp.route("/heritability-calculator/h2/<id>")
@jwt_required()
def heritability_result(id):
  title = "Heritability Results"
  alt_parent_breadcrumb = {"title": "Tools", "url": url_for('tools.tools')}
  user = get_current_user()
  hr = get_heritability_report(id)

  # If no such report exists, show an error message
  if hr is None:

    # Let admins know the report doesn't exist
    if user_is_admin():
      flash('This report does not exist', 'danger')
      abort(404)

    # For all other users, display a default "no access" message
    else:
      flash('You do not have access to that report', 'danger')
      abort(401)

  # If the user doesn't have permission to view this report, show an error message
  if not (hr.username == user.name or user_is_admin()):
    flash('You do not have access to that report', 'danger')
    abort(401)

  ready = False

  # Get blob paths
  # Used in code as well as templating(?)
  data_blob = hr.get_data_blob_path()
  result_blob = hr.get_result_blob_path()

  data_hash = hr.data_hash
  data_url = generate_blob_url(hr.get_bucket_name(), data_blob)

  data   = get_blob(hr.get_bucket_name(), data_blob)
  result = get_blob(hr.get_bucket_name(), result_blob)

  # get this dynamically from the bp
  # logs_url = f"/heritability/h2/{hr.id}/logs"
  logs_url = url_for('heritability_calculator.view_logs', id = hr.id)

  if data is None:
    return abort(404, description="Heritability report not found")

  data = data.download_as_string().decode('utf-8')
  data = pd.read_csv(io.StringIO(data), sep="\t")
  data['AssayNumber'] = data['AssayNumber'].astype(str)
  data['label'] = data.apply(lambda x: f"{x['AssayNumber']}: {x['Value']}", 1)
  data = data.to_dict('records')
  trait = data[0]['TraitName']
  # Get trait and set title
  subtitle = trait

  if result:
    hr.status = 'COMPLETE'
    hr.save()
    result = result.download_as_string().decode('utf-8')
    result = pd.read_csv(io.StringIO(result), sep="\t")
    result = result.to_dict('records')[0]

    fname =  datetime.today().strftime('%Y%m%d.')+trait
    ready = True

  format = '%I:%M %p %m/%d/%Y'
  now = datetime.now().strftime(format)

  try:
    operation_id = hr.operation_name.split('/').pop()
    operation = PipelineOperation(operation_id)
  except:
    operation = None

  service_name = os.getenv('HERITABILITY_CONTAINER_NAME')
  persistent_logger = PersistentLogger(service_name)
  error = persistent_logger.get(id)

  return render_template("tools/heritability_calculator/result.html", **locals())
