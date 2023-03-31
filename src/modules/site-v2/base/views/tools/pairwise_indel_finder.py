import re

from caendr.services.logger import logger
from flask import Response, Blueprint, render_template, request, url_for, jsonify, redirect, flash, abort

from base.forms import PairwiseIndelForm
from base.utils.auth import jwt_required, admin_required, get_current_user, user_is_admin
from base.utils.tools import lookup_report, try_submit

from caendr.models.datastore.browser_track import BrowserTrack, BrowserTrackDefault
from caendr.models.datastore import SPECIES_LIST, IndelPrimer
from caendr.models.error import NotFoundError, NonUniqueEntity, ReportLookupError, EmptyReportDataError, EmptyReportResultsError, UnfinishedReportError
from caendr.services.dataset_release import get_browser_tracks_path
from caendr.utils.constants import CHROM_NUMERIC

from caendr.services.indel_primer import (
    get_sv_strains,
    query_indels_and_mark_overlaps,
    create_new_indel_primer,
    get_indel_primer,
    get_all_indel_primers,
    get_user_indel_primers,
    fetch_indel_primer_report,
    modify_indel_primer_result,
)



# Tools blueprint
pairwise_indel_finder_bp = Blueprint(
  'pairwise_indel_finder', __name__, template_folder='tools'
)

from caendr.utils.constants import CHROM_NUMERIC



@pairwise_indel_finder_bp.route('/pairwise-indel-finder/tracks', methods=['GET'])
@jwt_required()
def get_tracks():

  # Get the Divergent Regions browser track
  try:
    divergent_track = BrowserTrackDefault.query_ds_unique('name', 'Divergent Regions', required=True)

  # If no track found, log an error message and continue raising with a more descriptive message
  except NotFoundError as ex:
    ex.description = 'Could not find Divergent Regions track.'
    logger.error(ex.description)
    raise ex

  # If track could not be uniquely identified, log an error and continue with the first result
  # TODO: Should this raise a further error?
  except NonUniqueEntity as ex:
    logger.error('Could not uniquely identify Divergent Regions track.')
    divergent_track = ex.matches[0]

  # Return the track parameters
  return jsonify(divergent_track['params'])


@pairwise_indel_finder_bp.route('/pairwise-indel-finder/strains', methods=['GET'])
@jwt_required()
def get_strains():
  return jsonify({
    species: get_sv_strains( species ) for species in SPECIES_LIST.keys()
  })



@pairwise_indel_finder_bp.route('/pairwise-indel-finder', methods=['GET'])
@jwt_required()
def pairwise_indel_finder():

  # Construct variables and render template
  return render_template('tools/pairwise_indel_finder/submit.html', **{

    # Page info
    "title": "Pairwise Indel Finder",
    "form":  PairwiseIndelForm(request.form),
    "alt_parent_breadcrumb": {
      "title": "Tools",
      "url":   url_for('tools.tools')
    },

    # Data
    "chroms":       CHROM_NUMERIC.keys(),
    "species_list": SPECIES_LIST,

    # Data locations
    "fasta_url": BrowserTrack.get_fasta_path_full(),

    # List of Species class fields to expose to the template
    # Optional - exposes all attributes if not provided
    'species_fields': [
      'name', 'short_name', 'project_num', 'wb_ver', 'latest_release',
    ],

    # String replacement tokens
    # Maps token to the field in Species object it should be replaced with
    'tokens': {
      'WB':      'wb_ver',
      'RELEASE': 'latest_release',
      'PRJ':     'project_num',
    },

    # Misc
    "fluid_container": True,
  })




@pairwise_indel_finder_bp.route("/pairwise-indel-finder/all-results")
@admin_required()
def all_results():
  return render_template('tools/pairwise_indel_finder/list-all.html', **{

    # Page info
    'title': "All Indel Primer Results",
    'alt_parent_breadcrumb': { "title": "Tools", "url": url_for('tools.tools') },

    # User info
    'user':  get_current_user(),
    'items': get_all_indel_primers(),
  })



@pairwise_indel_finder_bp.route("/pairwise-indel-finder/my-results")
@jwt_required()
def user_results():

  # Get user
  user = get_current_user()

  return render_template('tools/pairwise_indel_finder/list-user.html', **{

    # Page info
    'title': 'My Indel Primer Results',
    'alt_parent_breadcrumb': { "title": "Tools", "url": url_for('tools.tools'), },

    # User info
    'user':  user,
    'items': get_user_indel_primers(user.name),
  })



@pairwise_indel_finder_bp.route("/pairwise-indel-finder/query-indels", methods=["POST"])
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



@pairwise_indel_finder_bp.route('/pairwise-indel-finder/submit', methods=["POST"])
@jwt_required()
def submit():

  # Get current user
  user = get_current_user()

  # Get info about data
  data = request.get_json()

  # If user is admin, allow them to bypass cache with URL variable
  no_cache = bool(user_is_admin() and request.args.get("nocache", False))

  # Try submitting the job & getting a JSON status message
  response = try_submit(IndelPrimer, user, data, no_cache)

  # If there was an error, flash it
  if not response['succeeded']:
    flash(response['message'], 'danger')

  # Return the response
  return jsonify( response )



# TODO: Move internals of this to a service function
@pairwise_indel_finder_bp.route("/pairwise-indel-finder/result/<id>")
@pairwise_indel_finder_bp.route("/pairwise-indel-finder/result/<id>/tsv/<filename>")
@jwt_required()
def report(id, filename = None):

    # Fetch requested primer report
    # Ensures the report exists and the user has permission to view it
    try:
      report = lookup_report(IndelPrimer, id)

    # If the report lookup request is invalid, show an error message
    except ReportLookupError as ex:
      flash(ex.msg, 'danger')
      abort(ex.code)

    # Try getting the report data file and results
    try:
      data, result = fetch_indel_primer_report(report)
      ready = True

    # If report hasn't finished computing yet, display a waiting page
    except UnfinishedReportError as ex:
      data, result = ex.data, None
      ready = False

    # Error reading data JSON file
    # TODO: Should we mark report status as ERROR here too?
    except EmptyReportDataError:
      return abort(404, description="Pairwise indel finder data file not found")

    # Results file exists, but is empty - error
    except EmptyReportResultsError:
      report.status = 'ERROR'
      report.save()
      return abort(404, description="Pairwise indel finder report not found")

    # General error
    except Exception:
      return abort(404, description="Something went wrong")

    # Get indel information
    chrom, indel_start, indel_stop = re.split(":|-", data['site'])
    indel_start, indel_stop = int(indel_start), int(indel_stop)

    # Update the result object with computed fields and generate a format table
    # If result is None or empty, does nothing
    result, format_table = modify_indel_primer_result(result)

    # Update indel primer entity
    # TODO: Is this the right time/place for this?
    if ready:
      if report['status'] != 'ERROR':
        report['status'] = 'COMPLETE'
      report.empty = result is None
      report.save()

    # Return downloadable TSV of results
    # TODO: Shouldn't we check for filename? What if the ID ends in the characters "tsv"?
    if request.path.endswith("tsv"):
      return Response(format_table.to_csv(sep="\t"), mimetype="text/tab-separated-values")

    # Otherwise, return view page
    return render_template("tools/pairwise_indel_finder/view.html", **{

      # Page info
      'title':    f"Indel Primer Results {data['site']}",
      'subtitle': f"{data['strain_1']} | {data['strain_2']}",
      'alt_parent_breadcrumb': { "title": "Tools", "url": url_for('tools.tools') },

      # GCP data info
      'data_hash': report.data_hash,
      'id': id,

      # Job status
      'empty': result is None,
      'ready': ready,

      # Data
      'data':  data,
      'indel_start': indel_start,
      'indel_stop':  indel_stop,
      # 'size': data['size'],

      # Results
      'result': result,
      'records': result.to_dict('records') if (result is not None) else None,
      'format_table': format_table,
    })