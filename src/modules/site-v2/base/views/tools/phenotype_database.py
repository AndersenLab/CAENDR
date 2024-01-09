import bleach
from flask import (render_template,
                    url_for,
                    request,
                    redirect,
                    make_response,
                    jsonify,
                    flash,
                    abort,
                    Blueprint)
from extensions import cache, compress
from sqlalchemy import or_, func

from caendr.api.phenotype import query_phenotype_metadata, get_trait

from caendr.services.logger import logger

from base.forms                 import EmptyForm
from base.utils.auth            import jwt_required, get_current_user, user_is_admin
from base.utils.tools           import lookup_report, list_reports, try_submit

from caendr.models.datastore    import PhenotypeReport, Species, TraitFile
from caendr.models.error        import ReportLookupError, EmptyReportDataError, EmptyReportResultsError, NotFoundError
from caendr.models.job_pipeline import PhenotypePipeline
from caendr.models.status       import JobStatus
from caendr.models.sql          import PhenotypeMetadata



phenotype_database_bp = Blueprint(
  'phenotype_database', __name__, template_folder='templates'
)


def results_columns():
  return [
    {
      'title': 'Description',
      'class': 'label',
      'field': 'label',
      'width': 0.2,
      'link_to_data': True,
    },
    {
      'title': 'Trait 1',
      'class': 's1',
      'field': 'trait_1_name',
      'width': 0.4,
    },
    {
      'title': 'Trait 2',
      'class': 's2',
      'field': 'trait_2_name',
      'width': 0.4,
    },
  ]



#
# Main Endpoint
#

@phenotype_database_bp.route('')
@cache.memoize(60*60)
def phenotype_database():
  """
    Phenotype Database table (non-bulk)
  """
  # Get the list of traits for non-bulk files
  try:
    traits_non_bulk = query_phenotype_metadata()
  except Exception as ex:
    logger.error(f'Failed to retrieve the list of traits: {ex}')
    abort(500)

  return render_template('tools/phenotype_database/phenotypedb.html', **{
    # Page info
    "title": 'Phenotype Database and Analysis',
    "tool_alt_parent_breadcrumb": { "title": "Tools", "url": url_for('tools.tools') },

    # Data
    'traits': traits_non_bulk,
  })

@phenotype_database_bp.route('/traits-zhang')
@cache.memoize(60*60)
@compress.compressed()
def get_zhang_traits_json():
  """
    Phenotype Database table (bulk)
    Fetch table content by request for each page and render the data for Datatables()
  """
  try:
    # get parameters for query
    draw = request.args.get('draw', type=int)
    start = request.args.get('start', type=int)
    length = request.args.get('length', type=int)
    search_value = request.args.get('search[value]', '').lower()

    query = PhenotypeMetadata.query
    if search_value:
      query = query.filter(
        or_(
          func.lower(PhenotypeMetadata.trait_name_caendr.like(f"%{search_value}%")),
          func.lower(PhenotypeMetadata.trait_name_user.like(f"%{search_value}%")),
          func.lower(PhenotypeMetadata.description_short.like(f"%{search_value}%")),
          func.lower(PhenotypeMetadata.description_long.like(f"%{search_value}%")),
          func.lower(PhenotypeMetadata.source_lab.like(f"%{search_value}%")),
          func.lower(PhenotypeMetadata.institution.like(f"%{search_value}%")),
          func.lower(PhenotypeMetadata.submitted_by.like(f"%{search_value}%")),
        )
      )

    # Query PhenotypeMetadata (include phenotype values for each trait)
    data = query.offset(start).limit(length).from_self().\
      join(PhenotypeMetadata.phenotype_values).all()
    
    json_data = convert_joined_query_tojson(data)
    
    total_records = query.count()

    response_data = {
        "draw": draw,
        "recordsTotal": total_records,
        "recordsFiltered": total_records,
        "data": json_data
    }

  except Exception as ex:
    logger.error(f'Failed to retrieve the list of traits: {ex}')
    response_data = []
  return jsonify(response_data)

@phenotype_database_bp.route('/traits-list')
@cache.memoize(60*60)
@compress.compressed()
def get_traits_json():
  """
    Get traits data for non-bulk files in JSON format (include phenotype values)
  """
  try:
    traits_query = query_phenotype_metadata()
    traits_json = [ trait.to_json() for trait in traits_query]
    traits_json = convert_joined_query_tojson(traits_query)
  except Exception:
    traits_json = []
  return jsonify(traits_json)


#
# Submission Flow
#

@phenotype_database_bp.route('/submit/start')
def submit_start():
  return render_template('tools/phenotype_database/submit-start.html', **{
    # Page info
    'title': 'Phenotype Analysis',
    'tool_alt_parent_breadcrumb': {"title": "Tools", "url": url_for('tools.tools')},
    'initial_trait': request.args.get('trait'),
  })


@phenotype_database_bp.route('/submit/one', methods=['GET'], endpoint='submit_one')
@phenotype_database_bp.route('/submit/two', methods=['GET'], endpoint='submit_two')
def submit_traits():

  # Check for a URL var "trait" and use to lookup an initial trait
  initial_trait_name = request.args.get('trait')
  if initial_trait_name:
    try:
      initial_trait = TraitFile.get_ds(initial_trait_name, silent=False)
    except NotFoundError:
      flash('That trait could not be found.', 'danger')
      initial_trait = None
  else:
    initial_trait = None

  return render_template(f'tools/phenotype_database/submit-traits.html', **{
    # Page info
    'title': 'Phenotype Analysis',
    'tool_alt_parent_breadcrumb': {"title": "Tools", "url": url_for('tools.tools')},
    'form': EmptyForm(request.form),

    # Use the endpoint name (see route decorator above) to determine how many trait selectors to render
    'two_traits': request.endpoint.split('.')[-1] == 'submit_two',

    'species_list': Species.all(),
    'species_fields': [
      'name', 'short_name',
    ],

    'initial_trait': initial_trait,
  })


@phenotype_database_bp.route('/submit', methods=["POST"])
@jwt_required()
def submit():

  # Read & clean fields from JSON data
  data = {
    field: bleach.clean(request.json.get(field))
      for field in {'label', 'species', 'trait_1'}
  }

  trait_2 = request.json.get('trait_2')
  data['trait_2'] = bleach.clean(trait_2) if trait_2 is not None else None

  # If user is admin, allow them to bypass cache with URL variable
  no_cache = bool(user_is_admin() and request.args.get("nocache", False))

  # Try submitting the job & getting a JSON status message
  response, code = try_submit(PhenotypeReport.kind, get_current_user(), data, no_cache)

  # If there was an error, flash it
  if code != 200 and int(request.args.get('reloadonerror', 1)):
    flash(response['message'], 'danger')

  # Return the response
  return jsonify( response ), code


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
    job: PhenotypePipeline = lookup_report(PhenotypeReport.kind, id)

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

def convert_joined_query_tojson(q):
  """
    Convert PhenotypeMetadata query joined with PhenotypeDatabase to JSON
  """
  json_data = []
  for trait in q:
    phenotype_values = [ v.to_json() for v in trait.phenotype_values ]
    json_trait = trait.to_json()
    json_trait['phenotype_values'] = phenotype_values
    json_data.append(json_trait)
  return json_data