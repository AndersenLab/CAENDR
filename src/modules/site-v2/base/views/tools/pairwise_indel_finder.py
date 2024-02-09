import re

from caendr.services.logger import logger
from flask import Response, Blueprint, render_template, request, url_for, jsonify, redirect, flash, abort

from base.forms import PairwiseIndelForm
from base.utils.auth import jwt_required, admin_required, get_current_user, user_is_admin
from base.utils.tools import lookup_report, list_reports, try_submit

from caendr.models.datastore.browser_track import BrowserTrackDefault
from caendr.models.datastore import Species, IndelPrimerReport, DatasetRelease
from caendr.models.error import NotFoundError, NonUniqueEntity, ReportLookupError, EmptyReportDataError, EmptyReportResultsError
from caendr.models.job_pipeline import IndelFinderPipeline
from caendr.models.status import JobStatus
from caendr.services.dataset_release import get_dataset_release
from caendr.services.cloud.storage import BlobURISchema
from caendr.utils.bio import parse_chrom_interval
from caendr.utils.constants import CHROM_NUMERIC
from caendr.utils.data import get_file_format

from caendr.services.indel_primer import (
    get_sv_strains,
    query_indels_and_mark_overlaps,
)



# Tools blueprint
pairwise_indel_finder_bp = Blueprint(
  'pairwise_indel_finder', __name__, template_folder='tools'
)



def results_columns():
  return [
    {
      'title': 'Site',
      'class': 'site',
      'field': 'site',
      'width': 0.5,
      'link_to_data': True,
      'data_order': lambda e: e['site'],
    },
    {
      'title': 'Strain 1',
      'class': 's1',
      'field': 'strain_1',
      'width': 0.25,
    },
    {
      'title': 'Strain 2',
      'class': 's2',
      'field': 'strain_2',
      'width': 0.25,
    },
  ]

def try_get_sv_strains(species):
  try:
    return get_sv_strains(species)
  except:
    logger.error(f"Couldn't find strain variant annotations for {species}. Make sure the appropriate VCF file exists.")
    return []


## Data Endpoints

@pairwise_indel_finder_bp.route('/tracks', methods=['GET'])
@jwt_required()
def get_tracks():

  # Get the Divergent Regions browser track
  try:
    divergent_track = BrowserTrackDefault.query_ds_unique('name', 'Divergent Regions', required=True)

  # If no track found, log an error message and continue raising with a more descriptive message
  except NotFoundError as ex:
    logger.error(ex.description)
    raise ex

  # If track could not be uniquely identified, log an error and continue with the first result
  # TODO: Should this raise a further error?
  except NonUniqueEntity as ex:
    logger.error('Could not uniquely identify Divergent Regions track.')
    divergent_track = ex.matches[0]

  # If a species was passed, check that the referenced track file exists for this species
  # If not, return a 404 error
  # If species invalid, ignore (since this is an optional URL variable)
  species = Species.get(request.args.get('species'), from_url=True)
  if species and not divergent_track.check_exists_for_species(species):
      abort(404)

  # Return the track parameters
  return jsonify(divergent_track['params'])


@pairwise_indel_finder_bp.route('/strains', methods=['GET'])
@jwt_required()
def get_strains():
  return jsonify({
    species: try_get_sv_strains( species ) for species in Species.all().keys()
  })


## Page Endpoints

@pairwise_indel_finder_bp.route('', methods=['GET'])
@jwt_required()
def pairwise_indel_finder():

  # Construct variables and render template
  return render_template('tools/pairwise_indel_finder/submit.html', **{

    # Page info
    "title": "Pairwise Indel Finder",
    "form":  PairwiseIndelForm(request.form),
    "tool_alt_parent_breadcrumb": {
      "title": "Tools",
      "url":   url_for('tools.tools')
    },

    # Data
    "chroms":       CHROM_NUMERIC.keys(),
    "species_list": Species.all(),

    # Data locations
    'fasta_url': DatasetRelease.get_fasta_filepath_template(schema=BlobURISchema.HTTPS).get_string_safe(),

    # List of Species class fields to expose to the template
    # Optional - exposes all attributes if not provided
    'species_fields': [
      'name', 'short_name', 'project_num', 'wb_ver', 'release_latest',
    ],

    'latest_release_genomes': {
      species_name: get_dataset_release(species['release_latest'])['genome'] for species_name, species in Species.all().items()
    },

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



@pairwise_indel_finder_bp.route('/all-results', methods=['GET'], endpoint='all_results')
@pairwise_indel_finder_bp.route('/my-results',  methods=['GET'], endpoint='my_results')
@jwt_required()
def list_results():
  show_all = request.path.endswith('all-results')
  user = get_current_user()

  # Only show malformed Entities to admin users
  filter_errs = not user_is_admin()

  # Construct page
  return render_template('tools/report-list.html', **{

    # Page info
    'title': ('All' if show_all else 'My') + ' Primer Reports',
    'tool_alt_parent_breadcrumb': { "title": "Tools", "url": url_for('tools.tools'), },

    # User info
    'user':  user,

    # Tool info
    'tool_name': 'pairwise_indel_finder',
    'all_results': show_all,
    'button_labels': {
      'tool': 'New Primer Search',
      'all':  'All User Results',
      'user': 'My Primer Reports',
    },

    # Table info
    'species_list': Species.all(),
    'items': list_reports(IndelPrimerReport, None if show_all else user, filter_errs),
    'columns': results_columns(),

    'JobStatus': JobStatus,
  })



@pairwise_indel_finder_bp.route("/query-indels", methods=["POST"])
@jwt_required()
def query():

  # Validate query form
  form = PairwiseIndelForm()
  if form.validate_on_submit():

    # Extract fields
    species  = form.data['species']
    strain_1 = form.data['strain_1']
    strain_2 = form.data['strain_2']
    chrom    = form.data['chromosome']
    start    = form.data['start']
    stop     = form.data['stop']

    # Run query and return results
    results = query_indels_and_mark_overlaps(species, strain_1, strain_2, chrom, start, stop)
    return jsonify({ 'results': results })

  # If form not valid, return errors
  return jsonify({ 'errors': form.errors })



@pairwise_indel_finder_bp.route('/submit', methods=["POST"])
@jwt_required()
def submit():

  # Get current user
  user = get_current_user()

  # Get info about data
  data = request.get_json()

  # If user is admin, allow them to bypass cache with URL variable
  no_cache = bool(user_is_admin() and request.args.get("nocache", False))

  # Try submitting the job & getting a JSON status message
  response, code = try_submit(IndelPrimerReport.kind, user, data, no_cache)

  # If there was an error, flash it
  if code != 200 and int(request.args.get('reloadonerror', 1)):
    flash(response['message'], 'danger')

  # Return the response
  return jsonify( response ), code



@pairwise_indel_finder_bp.route("/report/<id>")
@pairwise_indel_finder_bp.route("/report/<id>/download/<file_ext>")
@jwt_required()
def report(id, file_ext=None):

    # Validate file extension, if provided
    if file_ext:
      file_format = get_file_format(file_ext, valid_formats={'csv'})
      if file_format is None:
        abort(404)
    else:
      file_format = None

    # Fetch requested primer report
    # Ensures the report exists and the user has permission to view it
    try:
      job: IndelFinderPipeline = lookup_report(IndelPrimerReport.kind, id)

    # If the report lookup request is invalid, show an error message
    except ReportLookupError as ex:
      flash(ex.msg, 'danger')
      abort(ex.code)


    # Try getting the report data file and results
    # If result is None, job hasn't finished computing yet
    try:
      data, result = job.fetch()
      ready = result is not None

    # Error reading one of the report files
    except (EmptyReportDataError, EmptyReportResultsError) as ex:
      logger.error(f'Error fetching Indel Finder report {ex.id}: {ex.description}')
      return abort(404, description = ex.description)

    # General error
    except Exception as ex:
      logger.error(f'Error fetching Indel Finder report {id}: {ex}')
      return abort(400, description = 'Something went wrong')

    # No data file found
    if data is None:
      logger.error(f'Error fetching Indel Finder report {id}: Input data file does not exist')
      return abort(404)


    # Get indel interval
    try:
      interval = parse_chrom_interval(data['site'])
      indel_start, indel_stop = interval['start'], interval['stop']
    except ValueError:
      logger.error(f'Invalid interval "{data["site"]}" for Indel Finder report {id}')
      indel_start, indel_stop = None, None

    # Extract the dataframe from the results
    dataframe = result.get('dataframe', None)

    # Update indel primer empty status
    if ready:
      job.report.empty = result['empty']  # TODO: 'empty' is no longer tracked as a prop. Should it be?
      job.report.save()


    # If a file format was specified, return a downloadable file with the results
    # TODO: Set a better filename?
    if file_format is not None:
      resp = Response(result['format_table'].to_csv(sep=file_format['sep']), mimetype=file_format['mimetype'])
      try:
        resp.headers['Content-Disposition'] = f'filename={job.report["species"]}_{job.report["strain_1"]}_{job.report["strain_2"]}_{data["site"]}.{file_ext}'
      except:
        resp.headers['Content-Disposition'] = f'filename={job.report["id"]}.{file_ext}'
      return resp


    # Otherwise, return view page
    return render_template("tools/pairwise_indel_finder/view.html", **{

      # Page info
      'title':    f"Indel Primer Results {data['site']}",
      'subtitle': f"{data['strain_1']} | {data['strain_2']}",
      'tool_alt_parent_breadcrumb': { "title": "Tools", "url": url_for('tools.tools') },

      # GCP data info
      'data_hash': job.report.data_hash,
      'id': id,

      # Job status
      'empty': result['empty'],
      'ready': ready,

      # Data
      'data':  data,
      'indel_start': indel_start,
      'indel_stop':  indel_stop,
      # 'size': data['size'],

      # Results
      'result':       dataframe,
      'records':      dataframe.to_dict('records') if (dataframe is not None) else None,
      'format_table': result.get('format_table'),
    })
