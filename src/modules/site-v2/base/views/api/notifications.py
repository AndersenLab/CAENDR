from flask import jsonify, Blueprint, url_for, abort, request

from caendr.services.logger import logger

from base.utils.auth  import admin_required
from base.utils.tools import lookup_report
from base.views.tools import pairwise_indel_finder_bp, genetic_mapping_bp, heritability_calculator_bp

from caendr.models.datastore import NemascanReport, HeritabilityReport, IndelPrimerReport, Announcement
from caendr.models.error     import ReportLookupError, NotFoundError
from caendr.models.status    import JobStatus
from caendr.services.email   import REPORT_SUCCESS_EMAIL_TEMPLATE, REPORT_ERROR_EMAIL_TEMPLATE
from caendr.services.cloud.secret import get_secret
from caendr.utils.json       import jsonify_request

API_SITE_ACCESS_TOKEN = get_secret('CAENDR_API_SITE_ACCESS_TOKEN')


api_notifications_bp = Blueprint('notifications', __name__)


REPORT_BP_MAP = {
  IndelPrimerReport.kind:  pairwise_indel_finder_bp.name,
  NemascanReport.kind:     genetic_mapping_bp.name,
  HeritabilityReport.kind: heritability_calculator_bp.name,
}


@api_notifications_bp.route('', methods=['GET'])
def notifications():
  abort(404)



#
# Job Status Notifications
#


@api_notifications_bp.route('/job-finish/<kind>/<id>/<status>', methods=['GET'])
def job_finish(kind, id, status):

  # Validate that this request came from the pipeline API
  access_token = request.headers.get('Authorization')
  if access_token != 'Bearer {}'.format(API_SITE_ACCESS_TOKEN):
    abort(403)

  # Fetch requested report, aborting if kind is invalid or report cannot be found
  try:
    job = lookup_report(kind, id, validate_user=False)
    report = job.report
  except ReportLookupError as ex:
    return ex.msg, ex.code

  # Lookup the blueprint name for this kind, aborting if kind is invalid
  try:
    bp = REPORT_BP_MAP[kind]
  except:
    return f'Invalid report type "{kind}"', 400

  # Complete message
  if status == JobStatus.COMPLETE:
    template = REPORT_SUCCESS_EMAIL_TEMPLATE.strip('\n')
    link     = url_for(bp + '.report', id=report.id, _external=True)

  # Error message
  elif status == JobStatus.ERROR:
    template = REPORT_ERROR_EMAIL_TEMPLATE.strip('\n')
    link     = url_for(bp + '.my_results', _external=True)

  # For any other status, return an error message
  else:
    return 'Invalid status for completion message.', 400

  # Generate plaintext and HTML versions of the body
  return jsonify({
    'text': template.format(
      report_type = report.get_report_display_name(),
      report_link = link,
    ),
    'html': template.replace('\n', '<br>').format(
      report_type = report.get_report_display_name(),
      report_link = f'<a>{link}</a>',
    ),
  })



#
# Site Announcements
#


@api_notifications_bp.route('/announcements', methods=['GET'])
@admin_required()
@jsonify_request
def announcement_list():
  '''
    Get the list of all site announcements.
  '''
  return {
    'data': [ e.serialize(include_name=True) for e in Announcement.query_ds() ]
  }


@api_notifications_bp.route('/announcement',                    methods=['POST'])
@api_notifications_bp.route('/announcement/<string:entity_id>', methods=['GET'])
@admin_required()
@jsonify_request
def announcement(entity_id: str):
  '''
    Manage one of the site announcements.

    Methods:
      GET:    Get the data for the given announcement ID.
      POST:   Create a new announcement.
  '''

  # GET Request
  # Return the list of announcement entities
  if request.method == 'GET':
    return Announcement.get_ds(entity_id).serialize()

  # POST Request
  # Create a new announcement, and return its unique ID
  if request.method == 'POST':
    new_announcement = Announcement(**request.get_json())
    new_announcement.save()
    return { 'id': new_announcement.name }

  # If somehow the method didn't match any of the above,
  # return a Method Not Allowed error
  return 405

