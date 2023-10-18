import requests

from caendr.services.logger import logger

from .cloudrun     import get_job_execution_status
from .lifesciences import get_pipeline_status

from caendr.models.datastore         import HeritabilityReport, NemascanReport, get_entity_by_kind
from caendr.models.error             import APINotFoundError, NotFoundError
from caendr.models.task              import TaskStatus
from caendr.services.email           import send_email
from caendr.services.cloud.datastore import query_ds_entities
from caendr.services.cloud.secret    import get_secret
from caendr.utils.env                import get_env_var



MODULE_SITE_HOST      = get_env_var('MODULE_SITE_HOST')
API_SITE_ACCESS_TOKEN = get_secret('CAENDR_API_SITE_ACCESS_TOKEN')
NO_REPLY_EMAIL        = get_secret('NO_REPLY_EMAIL')


NOTIFICATION_LOG_PREFIX = 'EMAIL_NOTIFICATION'



def make_dns_name_safe(s: str) -> str:
  '''
    Convert a string to DNS name format.

    Rules for this format:
      - May only contain alphanumeric characters & hyphens
      - Must start with a letter
      - Must not end with a hyphen
      - May be at most 64 characters long
  '''
  return s.lower().replace('_', '-')



def parse_operation_name(operation_name):
  '''
    Parse a GCP operation name into a dictionary of values,
    where each pair of strings in the name becomes a key:value pair.

    Example:
      projects/abc/locations/def -> { 'projects': 'abc', 'locations': 'def' }
  '''
  split_name = operation_name.split('/')
  return { split_name[i]: split_name[i+1] for i in range(0, len(split_name), 2) }




def get_operation_status(operation_name):
  '''
    Request the operation status from the correct pipeline, based on the service name.
  '''

  # Get the service & operation ID from the full operation name
  try:
    service, op_id = operation_name.split('/')[-2:]
  except:
    raise ValueError(f'Invalid operation name "{operation_name}"')

  # Life Sciences Pipeline
  if service == 'operations':
    logger.warn(f"[UPDATE {op_id}] Getting GLS pipeline status...")
    return get_pipeline_status(operation_name), service, op_id

  # Cloud Run Execution
  elif service == 'executions':
    logger.warn(f"[UPDATE {op_id}] Getting Cloud Run execution status...")
    return get_job_execution_status(operation_name), service, op_id

  # If nothing matched, return an error
  raise ValueError(f'Invalid service name "{service}".')



def update_all_linked_status_records(kind, operation_name):
  '''
    Update the Status fields of all reports linked to the given job.
    Sends a notification email to linked user(s) as necessary.
  '''

  logger.debug(f'update_all_linked_status_records: kind:{kind} operation_name:{operation_name}')

  # Get the operation status, plus the parsed service & id values
  try:
    status, service, op_id = get_operation_status(operation_name)

  # Operation could not be found
  except Exception as ex:
    raise APINotFoundError(f'Operation "{operation_name}" NOT FOUND -- nothing to do') from ex

  # Get task status from operation values
  done  = status.get('done')
  error = status.get('error')
  if error:
    logger.error(f"[UPDATE {op_id}] Error: Kind: {kind} Operation Name: {operation_name} error: {error}")
    status = TaskStatus.ERROR
  elif done:
    logger.debug(f"[UPDATE {op_id}] Complete: Kind: {kind} Operation Name: {operation_name}")
    status = TaskStatus.COMPLETE
  else:
    status = TaskStatus.RUNNING

  if kind is None:
    logger.warn(f'[UPDATE {op_id}] "kind" is undefined.')

  filters = [("operation_name", "=", operation_name)]
  ds_entities = query_ds_entities(kind, filters=filters, keys_only=True)
  for entity in ds_entities:

    # Retrieve the current status record as an Entity of the correct type
    try:
      status_record = get_entity_by_kind(kind, entity.key.name)
    except (ValueError, NotFoundError) as ex:
      logger.warn(f'[UPDATE {op_id}] Skipping status record update: {ex}')

    # Only send a notification if the report's status has not been updated yet
    # TODO: Should be able to remove kind check if all report notifications merged into one system
    should_send_notification = all([
      done,
      status_record['status'] not in [TaskStatus.COMPLETE, TaskStatus.ERROR],
      kind in [NemascanReport.kind, HeritabilityReport.kind],
    ])
    logger.debug(f'[{NOTIFICATION_LOG_PREFIX}] Should send notification for report {status_record.id}: {should_send_notification}. (done = {done}, kind = {kind}, current status = {status_record["status"]})')

    # Update the report status
    status_record.set_properties(status=status)
    status_record.save()

    # Send the notification, if applicable
    # In theory, doing this after the database update should prevent duplicate emails
    # For now, only send email notifications to admin users
    if not should_send_notification:
      return

    record_owner = status_record.get_user()
    email_result = None
    if record_owner is not None:
      logger.debug(f'[{NOTIFICATION_LOG_PREFIX}] Sending email notification for report {status_record.id} to {record_owner["email"]} (ID {record_owner.name}).')
      try:
        email_result = send_result_email(status_record, status)
      except Exception as ex:
        logger.error(f'[{NOTIFICATION_LOG_PREFIX}] Email failed to send: {ex}')
    else:
      logger.warn(f'[{NOTIFICATION_LOG_PREFIX}] Could not send email notification for report {status_record.id}: no user found. ({dict(status_record)})')

    if email_result:
      if email_result.status_code == 200:
        logger.debug(f'[{NOTIFICATION_LOG_PREFIX}] Email sent successfully ({email_result.status_code}): {email_result.text}')
      else:
        logger.error(f'[{NOTIFICATION_LOG_PREFIX}] Email failed to send ({email_result.status_code}): {email_result.text}')



def send_result_email(record, status):

  response = requests.get(
    f'https://{MODULE_SITE_HOST}/api/notifications/job-finish/{record.kind}/{record.id}/{status}',
    headers={
      'Content-Type':  'application/json',
      'Authorization': 'Bearer {}'.format(API_SITE_ACCESS_TOKEN),
    },
  )

  # Get the JSON body from the request
  if response.status_code != 200:
    return response
  message = response.json()

  # Send the email
  return send_email({
    "from":    f'CaeNDR <{NO_REPLY_EMAIL}>',
    "to":      record.get_user_email(),
    "subject": f'Your {record.get_report_display_name()} Report from CaeNDR.org',
    "text":    message['text'],
    "html":    message['html'],
  })
