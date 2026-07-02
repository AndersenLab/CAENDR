from flask import (render_template,
                    url_for,
                    request,
                    jsonify,
                    flash,
                    abort,
                    stream_with_context,
                    Response,
                    Blueprint)
from flask_jwt_extended import jwt_required, get_current_user
from extensions import cache
from datetime   import date

from caendr.api.phenotype import get_traits_with_metadata, get_trait_categories

from caendr.services.logger import logger

from base.forms                 import EmptyForm
from base.utils.auth            import user_is_admin, check_feature_flag_bp
from base.utils.tools           import list_reports, try_submit
from base.utils.view_decorators import parse_job_id, validate_form

from caendr.models.datastore    import PhenotypeReport, Species
from caendr.models.error        import NotFoundError
from caendr.models.job_pipeline import PhenotypePipeline
from caendr.models.trait        import Trait
from caendr.utils.data          import get_file_format, convert_data_to_download_file
from caendr.services.cloud.postgresql import db



phenotype_database_bp = Blueprint(
  'phenotype_database', __name__, template_folder='templates'
)


check_feature_flag_bp(phenotype_database_bp, 'PHENOTYPE_DB_ENABLED')



#
# Main Endpoint
#

@phenotype_database_bp.route('', methods=['GET', 'POST'])
@cache.memoize(60*60)
def phenotype_database():
  """
    Phenotype Database table (non-bulk)
  """
  form = EmptyForm()

  # Get the list of unique tags
  try:
    categories = get_trait_categories()

  except Exception as ex:
    logger.error(f'Failed to retrieve the list of traits: {ex}')
    abort(500, description='Failed to retrieve the list of traits')

  return render_template('tools/phenotype_database/phenotypedb.html', **{
    # Page info
    "title": 'Phenotype Database and Analysis',
    "tool_alt_parent_breadcrumb": { "title": "Tools", "url": url_for('tools.tools') },

    # Data
    'categories': categories,
    'form': form
  })

#
# Download Traits
#

@phenotype_database_bp.route('/download')
@cache.memoize(60*60)
def download_csv():
  """
    Download All Phenotype Traits as CSV
  """
  # Get the list of traits
  try:
    metadata_columns = ['submitted_by', 'species_name']
    traits = get_traits_with_metadata(metadata_columns)
  except Exception as ex:
    logger.error(f'Failed to retrieve the list of traits: {ex}')
    abort(500, description='Failed to retrieve the list of traits')
  
  file_format = get_file_format('csv', valid_formats=['csv'])

  # Set the column names
  columns = ['submitted_by', 'species_name', 'trait_name', 'strain_name', 'trait_value']

  def generate():
    yield file_format['sep'].join(columns) + '\n'
    try:
      for row in db.session.execute(traits.execution_options(yield_per=100)).all():
        row = [getattr(row, column) for column in columns]
        yield file_format['sep'].join(map(str, row)) + '\n'
    except Exception as ex:
      logger.error(f'Error during CSV generation: {ex}')

   # Stream the response as a file with the correct filename
  resp = Response(stream_with_context(generate()), mimetype=file_format['mimetype'])
  date_str = date.today().strftime('%Y-%m-%d')
  resp.headers['Content-Disposition'] = f'filename=phenotype_db_{date_str}.csv'
  return resp

#
# Submission Flow
#

@phenotype_database_bp.route('/submit/start')
@jwt_required()
def submit_start():
  return render_template('tools/phenotype_database/submit-start.html', **{
    # Page info
    'title': 'Phenotype Analysis',
    'tool_alt_parent_breadcrumb': {"title": "Tools", "url": url_for('tools.tools')},
  })


@phenotype_database_bp.route('/submit/one', methods=['GET'], endpoint='submit_one')
@phenotype_database_bp.route('/submit/two', methods=['GET'], endpoint='submit_two')
@jwt_required()
def submit_traits():

  # Check for URL vars specifying an initial trait
  # These will be inherited from submit_start
  initial_trait_id = request.args.get('trait')

  # Initialize variable to track whether initial trait belongs to user
  # Used to tell them whether it came from their MTL or not
  belongs_to_user = False

  # Try looking up the specified trait
  if initial_trait_id:
    try:
      initial_trait = Trait.from_id(initial_trait_id)
      belongs_to_user = initial_trait.file.belongs_to_user( get_current_user() )

    except (NotFoundError, ValueError):
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
    'belongs_to_user': belongs_to_user,
  })


@phenotype_database_bp.route('/submit', methods=["POST"])
@jwt_required()
@validate_form(None, from_json=True)
def submit(form_data, no_cache=False):

  # Make sure these keys exist in the form data, even if they weren't provided in the submission
  form_data['trait_2'] = form_data.get('trait_2', None)

  # Try submitting the job & getting a JSON status message
  response, code = try_submit(PhenotypeReport.kind, get_current_user(), form_data, no_cache)

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
  show_all = request.endpoint.endswith('all_results')
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
  })


@phenotype_database_bp.route("/report/<report_id>",                     methods=['GET'])
@phenotype_database_bp.route("/report/<report_id>/download/<file_ext>", methods=['GET'])
@jwt_required()
@parse_job_id(PhenotypePipeline)
def report(job: PhenotypePipeline, data, result, file_ext=None):

  # Validate file extension, if provided
  if file_ext:
    file_format = get_file_format(file_ext, valid_formats={'tsv'})
    if file_format is None:
      abort(404)
  else:
    file_format = None

  # If a file format was specified, return a downloadable file with the results
  if file_format is not None:
    columns = ['strain', *data['trait_names']]
    values  = sorted(result['trait_values'], key=lambda v: v[0])
    resp = Response(convert_data_to_download_file( values, columns, file_ext=file_ext ), mimetype=file_format['mimetype'])
    try:
      resp.headers['Content-Disposition'] = f'filename={job.report["species"]}_{"_".join(job.report.trait_names)}.{file_ext}'
    except:
      resp.headers['Content-Disposition'] = f'filename={job.report.id}.{file_ext}'
    return resp

  # Otherwise, return view page
  return render_template('tools/phenotype_database/report.html', **{
    'title': 'Phenotype Analysis Report',
    'tool_alt_parent_breadcrumb': {"title": "Tools", "url": url_for('tools.tools')},

    'report': job.report,
    'data':   data,
    'result': result,
    'ready':  True,
    'error':  job.get_error(),
  })
