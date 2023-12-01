from caendr.services.logger import logger
from flask import Response, Blueprint, render_template, request, url_for, jsonify, redirect, flash, abort

from base.utils.auth         import jwt_required, get_current_user
from base.utils.tools        import lookup_report

from caendr.models.datastore import PhenotypeReport
from caendr.models.error     import ReportLookupError, EmptyReportDataError, EmptyReportResultsError
from caendr.models.status    import JobStatus



phenotype_comparison_bp = Blueprint(
  'phenotype_comparison', __name__, template_folder='templates'
)



@phenotype_comparison_bp.route('/')
def phenotype_comparison():
  pass



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

  return render_template('tools/phenotype_db/phenotype.html', **{
    'title': "Phenotype Results",
    'tool_alt_parent_breadcrumb': {"title": "Tools", "url": url_for('tools.tools')},

    'report': job.report,
    'data':   data,
    'result': result,
    'ready':  True,
    'error':  job.get_error(),

    'JobStatus': JobStatus,
  })

