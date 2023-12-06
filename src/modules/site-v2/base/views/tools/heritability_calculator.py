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

from base.forms import HeritabilityForm
from base.utils.auth import jwt_required, admin_required, get_jwt, get_current_user, user_is_admin
from base.utils.tools import try_submit
from base.utils.view_decorators import parse_job_id, validate_form

from caendr.models.datastore import Species, HeritabilityReport
from caendr.models.status import JobStatus
from caendr.models.job_pipeline import HeritabilityPipeline
from caendr.api.strain import get_strains
from caendr.services.heritability_report import get_heritability_report, get_heritability_reports
from caendr.utils.data import unique_id, get_object_hash
from caendr.utils.env import get_env_var
from caendr.services.cloud.storage import generate_blob_uri, BlobURISchema
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
@validate_form(HeritabilityForm, err_msg='You must include a description of your data and a CSV file to upload.')
def submit(form_data, no_cache=False):

  # Try submitting the job & returning a JSON status message
  response, code = try_submit( HeritabilityReport.kind, get_current_user(), form_data, no_cache=no_cache )

  # If there was an error, flash it
  if code != 200 and int(request.args.get('reloadonerror', 1)):
    flash(response['message'], 'danger')

  # If the response contains a caching message, flash it
  elif response.get('message') and response.get('ready', False):
    flash(response.get('message'), 'success')

  # Return the response
  return jsonify( response ), code


@heritability_calculator_bp.route("/report/<report_id>/logs")
@jwt_required()
@parse_job_id(HeritabilityPipeline, fetch=False)
def view_logs(job: HeritabilityPipeline):

  # Collect all the log files in this report's work folder
  blobs = job.report.list_work_directory(
    filter=lambda blob: 'google/logs/action' in blob.name or '.command' in blob.name
  )

  # Filter out all empty log files
  logs = []
  for blob in blobs:
    data = blob.download_as_string().decode('utf-8').strip()
    if data != '':
      logs.append({ 'blob_name': blob.name, 'data': data })

  return render_template("tools/heritability_calculator/logs.html", logs=logs)


@heritability_calculator_bp.route("/report/<report_id>", methods=['GET'])
@jwt_required()
@parse_job_id(HeritabilityPipeline)
def report(job: HeritabilityPipeline, data, result):

  ready = result is not None
  trait = data[0]['TraitName']

  # # TODO: Is this used? It looks like the error message(s) come from the entity's PipelineOperation
  # service_name = os.getenv('HERITABILITY_CONTAINER_NAME')
  # persistent_logger = PersistentLogger(service_name)
  # error = persistent_logger.get(job.report.id)

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
    'logs_url': url_for('heritability_calculator.view_logs', report_id = job.report.id),

    'JobStatus': JobStatus,
  })
