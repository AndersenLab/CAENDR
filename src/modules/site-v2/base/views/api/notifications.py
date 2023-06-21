from flask import jsonify, Blueprint, url_for, abort, request

from base.utils.tools import lookup_report
from base.views.tools import pairwise_indel_finder_bp, genetic_mapping_bp, heritability_calculator_bp

from caendr.models.datastore import NemascanMapping, HeritabilityReport, IndelPrimer
from caendr.models.error     import ReportLookupError
from caendr.models.task      import TaskStatus
from caendr.services.email   import REPORT_SUCCESS_EMAIL_TEMPLATE, REPORT_ERROR_EMAIL_TEMPLATE
from caendr.services.cloud.secret import get_secret

API_SITE_ACCESS_TOKEN = get_secret('CAENDR_API_SITE_ACCESS_TOKEN')


api_notifications_bp = Blueprint('notifications', __name__)


REPORT_BP_MAP = {
  IndelPrimer.kind:        pairwise_indel_finder_bp.name,
  NemascanMapping.kind:    genetic_mapping_bp.name,
  HeritabilityReport.kind: heritability_calculator_bp.name,
}


@api_notifications_bp.route('', methods=['GET'])
def notifications():
  abort(404)


@api_notifications_bp.route('/job-finish/<kind>/<id>/<status>', methods=['GET'])
def job_finish(kind, id, status):

  # Validate that this request came from the pipeline API
  access_token = request.headers.get('Authorization')
  if access_token != 'Bearer {}'.format(API_SITE_ACCESS_TOKEN):
    abort(403)

  # Fetch requested report, aborting if kind is invalid or report cannot be found
  try:
    report = lookup_report(kind, id, validate_user=False)
  except ReportLookupError as ex:
    return ex.msg, ex.code

  # Lookup the blueprint name for this kind, aborting if kind is invalid
  try:
    bp = REPORT_BP_MAP[kind]
  except:
    return f'Invalid report type "{kind}"', 400

  # Complete message
  if status == TaskStatus.COMPLETE:
    template = REPORT_SUCCESS_EMAIL_TEMPLATE.strip('\n')
    link     = url_for(bp + '.report', id=report.id, _external=True)

  # Error message
  elif status == TaskStatus.ERROR:
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
