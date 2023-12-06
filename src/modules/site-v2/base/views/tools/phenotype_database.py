import json
from flask import (render_template,
                    url_for,
                    request,
                    redirect,
                    make_response,
                    jsonify,
                    flash,
                    abort,
                    Blueprint)
from extensions import cache

from caendr.services.logger import logger

from base.utils.auth         import jwt_required, get_current_user
from base.utils.tools        import lookup_report

from caendr.models.datastore import PhenotypeReport
from caendr.models.error     import ReportLookupError, EmptyReportDataError, EmptyReportResultsError
from caendr.models.status    import JobStatus



phenotype_database_bp = Blueprint(
  'phenotype_database', __name__, template_folder='templates'
)



#
# Main Endpoint
#

@phenotype_database_bp.route('')
@cache.memoize(60*60)
def phenotype_database():
  return render_template('tools/phenotype_database/phenotypedb.html', **{
    # Page info
    "title": 'Phenotype Database and Analysis',
    "tool_alt_parent_breadcrumb": { "title": "Tools", "url": url_for('tools.tools') },
  })


#
# Submission Flow
#

@phenotype_database_bp.route('/analysis/stepA')
def analysisA():
  return render_template('tools/phenotype_database/phenotypeAnalysisA.html', **{
    # Page info
    'title': 'Phenotype Analysis',
    'tool_alt_parent_breadcrumb': {"title": "Tools", "url": url_for('tools.tools')},
  })

@phenotype_database_bp.route('/analysis/stepB')
def analysisB():
  return render_template('tools/phenotype_database/phenotypeAnalysisB.html', **{
    # Page info
    'title': 'Phenotype Analysis',
    'tool_alt_parent_breadcrumb': {"title": "Tools", "url": url_for('tools.tools')},
  })

@phenotype_database_bp.route('/analysis/stepC')
def analysisC():
  return render_template('tools/phenotype_database/phenotypeAnalysisC.html', **{
    # Page info
    'title': 'Phenotype Analysis',
    'tool_alt_parent_breadcrumb': {"title": "Tools", "url": url_for('tools.tools')},
  })


#
# Results
#

@phenotype_database_bp.route("/report/<id>", methods=['GET'])
@jwt_required()
def report(id):

  # Fetch requested phenotype report
  # Ensures the report exists and the user has permission to view it
  try:
    job = lookup_report(PhenotypeReport.kind, id)

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

  return render_template('tools/phenotype_database/report.html', **{
    'title': 'Phenotype Analysis Report',
    'tool_alt_parent_breadcrumb': {"title": "Tools", "url": url_for('tools.tools')},

    'report': job.report,
    'data':   data,
    'result': result,
    'ready':  True,
    'error':  job.get_error(),

    'JobStatus': JobStatus,
  })
