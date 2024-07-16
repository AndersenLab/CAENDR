# Flask Imports
from flask import Blueprint, render_template, request, url_for, jsonify, redirect, flash, abort

from caendr.services.logger import logger

# Site Module Imports
from base.forms                      import GuideRNASelectionForm
from base.utils.auth                 import jwt_required, admin_required, get_current_user, user_is_admin
from base.utils.tools                import list_reports, try_submit
from base.utils.view_decorators      import parse_job_id, validate_form, display_or_download

# CaeNDR Package Imports
from caendr.models.datastore         import Species, DatasetRelease
from caendr.services.dataset_release import get_dataset_release
from caendr.services.cloud.storage   import BlobURISchema
from caendr.utils.constants          import CHROM_NUMERIC
from caendr.utils.data               import DownloadFile

# gRNA Selection Tool Imports
from caendr.models.datastore             import GuideRNAReport
from caendr.models.job_pipeline          import GuideRNAPipeline
from caendr.services.guide_rna_selection import query_grna_selection



# Tools blueprint
guide_rna_selection_bp = Blueprint(
  'guide_rna_selection', __name__, template_folder='tools'
)



#
# Main Page
#


@guide_rna_selection_bp.route('', methods=['GET'])
@jwt_required()
def guide_rna_selection():

  # Construct variables and render template
  return render_template('tools/guide_rna_selection/guide-rna-selection.html', **{

    # Page info
    "title": "Guide RNA Selection",
    "tool_alt_parent_breadcrumb": {
      "title": "Tools",
      "url":   url_for('tools.tools')
    },
    "form": GuideRNASelectionForm(request.form),

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



#
# Results Pages
#


@guide_rna_selection_bp.route('/all-results', methods=['GET'], endpoint='all_results')
@guide_rna_selection_bp.route('/my-results',  methods=['GET'], endpoint='my_results')
@jwt_required()
def list_results():
  show_all = request.endpoint.endswith('all_results')
  user = get_current_user()

  # Only show malformed Entities to admin users
  filter_errs = not user_is_admin()

  # Construct page
  return render_template('tools/report-list.html', **{

    # Page info
    'title': ('All' if show_all else 'My') + ' gRNA Site Reports',
    'tool_alt_parent_breadcrumb': { "title": "Tools", "url": url_for('tools.tools'), },

    # User info
    'user':  user,

    # Tool info
    'tool_name': 'guide_rna_selection',
    'all_results': show_all,
    'button_labels': {
      'tool': 'New gRNA Site Report',
      'all':  'All User Reports',
      'user': 'My gRNA Site Reports',
    },

    # Table info
    'species_list': Species.all(),
    'items': list_reports(GuideRNAReport, None if show_all else user, filter_errs),
  })


@guide_rna_selection_bp.route("/report/<report_id>",                     methods=['GET'])
@guide_rna_selection_bp.route("/report/<report_id>/download/<file_ext>", methods=['GET'])
@jwt_required()
@parse_job_id(GuideRNAPipeline)
@display_or_download({'csv'})
def report(job: GuideRNAPipeline, data, result, downloading=False):

    # If a download endpoint is being called, return the results table as a downloadable file
    # Return as a DownloadFile object (required by display_or_download decorator)
    if downloading:
      return DownloadFile( job.report.download_name, result.get('dataframe'), index=False )

    # Otherwise, return view page
    return render_template("tools/guide_rna_selection/report.html", **{

      # Page info
      'title':    f'gRNA Sites {data["site"]}',
      'subtitle': ' | '.join(job.report.strains),
      'tool_alt_parent_breadcrumb': { "title": "Tools", "url": url_for('tools.tools') },

      # GCP data info
      'data_hash': job.report.data_hash,
      'report_id': job.report.id,

      # Data & Results
      'data':  data,
      'empty': False,
      'result': result.get('data', {}),
    })



#
# POST Request Endpoints
#


@guide_rna_selection_bp.route("/query", methods=["POST"])
@jwt_required()
@validate_form(GuideRNASelectionForm)
def query(form_data, no_cache=False):
  '''
    Query a given region.
  '''

  # Pass the form fields to the query function & return the result
  return jsonify({ 'results': query_grna_selection(**form_data) })



@guide_rna_selection_bp.route('/submit', methods=["POST"])
@jwt_required()
@validate_form(None, from_json=True)
def submit(form_data, no_cache=False):
  '''
    Submit a new report.
  '''

  # Try submitting the job & getting a JSON status message
  response, code = try_submit(GuideRNAReport.kind, get_current_user(), form_data, no_cache)

  # If there was an error, flash it
  if code != 200 and int(request.args.get('reloadonerror', 1)):
    flash(response['message'], 'danger')

  # Return the response
  return jsonify( response ), code
