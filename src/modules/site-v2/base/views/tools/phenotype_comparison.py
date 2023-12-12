import bleach
from caendr.services.logger import logger
from flask import Response, Blueprint, render_template, request, url_for, jsonify, redirect, flash, abort

from base.forms              import PhenotypeComparisonForm
from base.utils.auth         import jwt_required, get_current_user, user_is_admin
from base.utils.tools        import lookup_report, try_submit

from caendr.models.datastore import Species, PhenotypeReport
from caendr.models.error     import ReportLookupError, EmptyReportDataError, EmptyReportResultsError
from caendr.models.status    import JobStatus



phenotype_comparison_bp = Blueprint(
  'phenotype_comparison', __name__, template_folder='templates'
)



@phenotype_comparison_bp.route('/')
def phenotype_comparison():

  # Construct variables and render template
  return render_template('tools/phenotype/submit.html', **{

    # Page info
    "title": "Phenotype Comparison",
    "form":  PhenotypeComparisonForm(request.form),
    "tool_alt_parent_breadcrumb": {
      "title": "Tools",
      "url":   url_for('tools.tools')
    },

    # List of Species class fields to expose to the template
    "species_list": Species.all(),
    'species_fields': [
      'name', 'short_name', 'project_num', 'wb_ver', 'release_latest',
    ],

    # String replacement tokens
    # Maps token to the field in Species object it should be replaced with
    'tokens': {
      'WB':      'wb_ver',
      'RELEASE': 'release_latest',
      'PRJ':     'project_num',
      'GENOME':  'fasta_genome',
    },

    # Misc
    "fluid_container": True,
  })



@phenotype_comparison_bp.route('/submit', methods=["POST"])
@jwt_required()
def submit():
  form = PhenotypeComparisonForm(request.form)
  user = get_current_user()

  # Validate form fields
  # Checks that species is in species list & label is not empty
  if not form.validate_on_submit():
    msg = "Invalid submission"
    flash(msg, "danger")
    return jsonify({ 'message': msg }), 400

  # Read fields from form
  data = {
    field: bleach.clean(request.form.get(field))
      for field in {'label', 'species', 'trait_1', 'trait_2'}
  }

  # If user is admin, allow them to bypass cache with URL variable
  no_cache = bool(user_is_admin() and request.args.get("nocache", False))

  # Try submitting the job & getting a JSON status message
  response, code = try_submit(PhenotypeReport.kind, user, data, no_cache)

  # If there was an error, flash it
  if code != 200 and int(request.args.get('reloadonerror', 1)):
    flash(response['message'], 'danger')

  # Return the response
  return jsonify( response ), code



@phenotype_comparison_bp.route("/report/<id>", methods=['GET'])
@jwt_required()
def report(id):

  user = get_current_user()

  # Fetch requested phenotype report
  # Ensures the report exists and the user has permission to view it
  try:
    job = lookup_report(PhenotypeReport.kind, id, user=user)

  # If the report lookup request is invalid, show an error message
  except ReportLookupError as ex:
    flash(ex.msg, 'danger')
    abort(ex.code)

  # Try getting & parsing the report data file and results
  # If result is None, job hasn't finished computing yet
  try:
    data, result = job.fetch()

  # Error reading one of the report files
  except (EmptyReportDataError, EmptyReportResultsError) as ex:
    logger.error(f'Error fetching Phenotype report {ex.id}: {ex.description}')
    return abort(404, description = ex.description)

  # General error
  except Exception as ex:
    logger.error(f'Error fetching Phenotype report {id}: {ex}')
    return abort(400, description = 'Something went wrong')

  # No data file found
  if data is None:
    logger.error(f'Error fetching Phenotype report {id}: Input data does not exist')
    return abort(404)

  return render_template('tools/phenotype/report.html', **{
    'title': "Phenotype Results",
    'tool_alt_parent_breadcrumb': {"title": "Tools", "url": url_for('tools.tools')},

    'report': job.report,
    'data':   data,
    'result': result,
    'ready':  True,
    'error':  job.get_error(),

    'JobStatus': JobStatus,
  })

