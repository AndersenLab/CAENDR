from flask import jsonify, Blueprint, url_for, abort, request

from caendr.services.logger import logger

from base.forms       import AnnouncementForm
from base.utils.auth  import access_token_required, admin_required
from base.utils.tools import lookup_report
from base.views.tools import pairwise_indel_finder_bp, genetic_mapping_bp, heritability_calculator_bp

from base.utils.view_decorators import parse_entity_id, validate_form

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
@access_token_required(API_SITE_ACCESS_TOKEN)
def job_finish(kind, id, status):

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
    link     = url_for(bp + '.report', report_id=report.id, _external=True)

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
    'data': [ e.serialize(include_name=True) for e in Announcement.query_ds(deleted=False) ]
  }


@api_notifications_bp.route('/announcements/order', methods=['POST'])
@admin_required()
@jsonify_request
def announcements_reorder():
  '''
    Change the order of the given announcements.

    Expects body as mapping from announcement ID to new order.
    Any announcements not given in the body will not be changed.

    It is on the caller to ensure the new order is consistent, i.e. that no two announcements
    have the same order.  In this case, their order will be undefined.

    TODO: Should this function just take a list of IDs in the desired order,
          and assign the order field "implicitly"?
  '''

  # Retrieve all announcements in the request body, aborting if any lookup fails
  try:
    announcements = [
      (Announcement.get_ds(announcement_id, silent=False), new_order)
        for (announcement_id, new_order) in request.json.items()
    ]
  except NotFoundError as ex:
    abort(422, description=ex.description)
  except Exception as ex:
    abort(400)

  # Update all the orders locally
  for announcement, new_order in announcements:
    announcement['order'] = new_order

  # Save new order in one batch transaction
  # If this fails, it should all fail together
  Announcement.save_batch(*[announcement for (announcement, new_order) in announcements])

  # Return success
  return {}


@api_notifications_bp.route('/announcement',                    methods=['POST'])
@api_notifications_bp.route('/announcement/<string:entity_id>', methods=['GET', 'PATCH', 'DELETE'])
@admin_required()
@parse_entity_id(Announcement, required=False, kw_name_id='entity_id', kw_name_entity='announcement')
@validate_form(AnnouncementForm, methods=['POST', 'PATCH'])
@jsonify_request
def announcement(announcement: Announcement = None, form_data = None, no_cache: bool = False):
  '''
    Manage one of the site announcements.

    Methods:
      GET:    Get the data for the given announcement ID.
      POST:   Create a new announcement.
      PATCH:  Update an existing announcement.
      DELETE: Delete an existing announcement.
  '''

  # GET Request
  # Return the list of announcement entities
  if request.method == 'GET':
    return announcement.serialize()

  # POST Request
  # Create a new announcement, and return its unique ID
  if request.method == 'POST':
    new_announcement = Announcement(**{
      prop: form_data.get(prop) for prop in Announcement.get_props_set()
    })
    new_announcement.save()
    return { 'id': new_announcement.name }

  # PATCH Request
  # Lookup the desired announcement and update its properties
  if request.method == 'PATCH':

    # Extract the new property values from the form, casting "active" to a bool
    new_values = {
      prop: form_data.get(prop)
        for prop in Announcement.get_props_set()
        if form_data.get(prop) is not None
    }
    if form_data.get('active') is not None:
      new_values['active'] = form_data.get('active') == 'true'

    # Update the announcement object
    announcement.set_properties(**new_values)
    announcement.save()
    return { 'id': announcement.name }

  # DELETE Request
  # Lookup the desired announcement and soft delete it
  if request.method == 'DELETE':
    announcement.soft_delete()
    announcement.save()
    return {}, 200

  # If somehow the method didn't match any of the above,
  # return a Method Not Allowed error
  abort(405)
