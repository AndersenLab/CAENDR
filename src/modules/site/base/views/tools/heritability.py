import io
import os
import pandas as pd
import json
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
from logzero import logger
from datetime import datetime

from base.forms import HeritabilityForm
from base.utils.auth import jwt_required, admin_required, get_jwt, get_current_user

from caendr.models.error import CachedDataError, DuplicateDataError
from caendr.api.strain import get_strains
from caendr.services.heritability_report import get_all_heritability_results, get_user_heritability_results, create_new_heritability_report, get_heritability_report
from caendr.utils.data import unique_id, convert_data_table_to_tsv, get_object_hash
from caendr.services.cloud.storage import get_blob, generate_blob_url
from caendr.services.persistent_logger import PersistentLogger

# ================== #
#   heritability     #
# ================== #

# Tools blueprint
heritability_bp = Blueprint('heritability',
                            __name__)


@heritability_bp.route('/heritability')
def heritability():
  title = "Heritability Calculator"
  alt_parent_breadcrumb = {"title": "Tools", "url": url_for('tools.tools')}
  form = HeritabilityForm()
  hide_form = True
  strain_list = []
  return render_template('tools/heritability/submit.html', **locals())


@heritability_bp.route('/heritability/create', methods=["GET"])
@jwt_required()
def heritability_create():
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
  return render_template('tools/heritability/submit.html', **locals())


@heritability_bp.route("/heritability/all-results")
@admin_required()
def heritability_all_results():
  title = "All Heritability Results"
  alt_parent_breadcrumb = {"title": "Tools", "url": url_for('tools.tools')}
  user = get_current_user()
  items = get_all_heritability_results()
  return render_template('tools/heritability/list-all.html', **locals())


@heritability_bp.route("/heritability/my-results")
@jwt_required()
def heritability_user_results():
  title = "My Heritability Results"
  alt_parent_breadcrumb = {"title": "Tools", "url": url_for('tools.tools')}
  user = get_current_user()
  items = get_user_heritability_results(user.name)
  return render_template('tools/heritability/list-user.html', **locals())


@heritability_bp.route('/heritability/submit', methods=["POST"])
@jwt_required()
def submit_h2():
  user = get_current_user()
  label = request.values['label']
  columns = ["AssayNumber", "Strain", "TraitName", "Replicate", "Value"]

  # Extract table data
  data = json.loads(request.values['table_data'])
  data = [x for x in data[1:] if x[0] is not None]
  trait = data[0][2]

  data_tsv = convert_data_table_to_tsv(data, columns)

  # Generate an ID for the data based on its hash
  data_hash = get_object_hash(data, length=32)
  logger.debug(data_hash)
  id = unique_id()

  try:
    h = create_new_heritability_report(id, user.name, label, data_hash, trait, data_tsv)
  except DuplicateDataError:
      flash('Oops! It looks like you submitted that data already - redirecting to your list of Heritability Reports', 'danger')
      return jsonify({'duplicate': True,
              'data_hash': data_hash,
              'id': id})
  except CachedDataError:
      flash('Oops! It looks like that data has already been submitted - redirecting to the saved results', 'danger')
      return jsonify({'cached': True,
                  'data_hash': data_hash,
                  'id': id})
  except Exception as ex:
      flash("Oops! There was a problem submitting your request: {ex}", 'danger')
      return jsonify({'duplicate': True,
              'data_hash': data_hash,
              'id': id})

  return jsonify({'started': True,
                'data_hash': data_hash,
                'id': id})


# TODO: Move this into a separate service
@heritability_bp.route("/heritability/h2/<id>")
@jwt_required()
def heritability_result(id):
  title = "Heritability Results"
  alt_parent_breadcrumb = {"title": "Tools", "url": url_for('tools.tools')}
  user = get_current_user()
  hr = get_heritability_report(id)
  ready = False
  data_url = generate_blob_url(hr.get_bucket_name(), hr.get_data_blob_path())

  if (not hr._exists) or (hr.username != user.name):
    flash('You do not have access to that report', 'danger')
    abort(401)

  data_hash = hr.data_hash
  data_blob = hr.get_data_blob_path()
  result_blob = hr.get_result_blob_path()
  data = get_blob(hr.get_bucket_name(), hr.get_data_blob_path())
  result = get_blob(hr.get_bucket_name(), hr.get_result_blob_path())


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

  return render_template("tools/heritability/view.html", **locals())

