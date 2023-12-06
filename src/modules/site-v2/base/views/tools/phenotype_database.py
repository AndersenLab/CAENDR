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

from base.utils.auth         import jwt_required, get_current_user, user_is_admin
from base.utils.tools        import lookup_report, list_reports

from caendr.models.datastore import PhenotypeReport, Species
from caendr.models.error     import ReportLookupError, EmptyReportDataError, EmptyReportResultsError
from caendr.models.status    import JobStatus



phenotype_database_bp = Blueprint(
  'phenotype_database', __name__, template_folder='templates'
)


def results_columns():
  return [
    {
      'title': 'Description',
      'class': 'label',
      'field': 'label',
      'width': 0.5,
      'link_to_data': True,
    },
    {
      'title': 'Trait 1',
      'class': 's1',
      'field': 'trait_1_name',
      'width': 0.25,
    },
    {
      'title': 'Trait 2',
      'class': 's2',
      'field': 'trait_2_name',
      'width': 0.25,
    },
  ]



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

@phenotype_database_bp.route('/all-results', methods=['GET'], endpoint='all_results')
@phenotype_database_bp.route('/my-results',  methods=['GET'], endpoint='my_results')
@jwt_required()
def list_results():
  show_all = request.path.endswith('all-results')
  user = get_current_user()

  # Only show malformed Entities to admin users
  filter_errs = not user_is_admin()

  # Construct page
  return render_template('tools/report-list.html', **{

    # Page info
    'title': ('All' if show_all else 'My') + ' Phenotype Reports',
    'tool_alt_parent_breadcrumb': { "title": "Tools", "url": url_for('tools.tools'), },

    # User info
    'user':  user,

    # Tool info
    'tool_name': 'phenotype_database',
    'all_results': show_all,
    'button_labels': {
      'tool': 'New Phenotype Report',
      'all':  'All User Results',
      'user': 'My Phenotype Reports',
    },

    # Table info
    'species_list': Species.all(),
    'items': list_reports(PhenotypeReport, user = None if show_all else user, filter_errs=filter_errs),
    'columns': results_columns(),

    'JobStatus': JobStatus,
  })


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
