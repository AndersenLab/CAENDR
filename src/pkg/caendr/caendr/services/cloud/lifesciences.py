import os
import requests

from caendr.models.datastore.heritability_report import HeritabilityReport
from caendr.models.task import TaskStatus

from caendr.services.logger import logger
from googleapiclient import discovery
from oauth2client.client import GoogleCredentials

from caendr.models.datastore import PipelineOperation, DatabaseOperation, NemascanMapping, IndelPrimer
from caendr.models.error import PipelineRunError
from caendr.services.cloud.datastore import query_ds_entities
from caendr.services.cloud.service_account import authenticate_google_service
from caendr.services.cloud.secret import get_secret
from caendr.services.email import send_email
from caendr.utils.env import get_env_var
from caendr.utils.json import get_json_from_class


GOOGLE_CLOUD_PROJECT_NUMBER = os.environ.get('GOOGLE_CLOUD_PROJECT_NUMBER')
GOOGLE_CLOUD_REGION = os.environ.get('GOOGLE_CLOUD_REGION')
MODULE_API_PIPELINE_TASK_SERVICE_ACCOUNT_NAME = os.environ.get('MODULE_API_PIPELINE_TASK_SERVICE_ACCOUNT_NAME')
MODULE_SITE_HOST = get_env_var('MODULE_SITE_HOST')

API_SITE_ACCESS_TOKEN = get_secret('CAENDR_API_SITE_ACCESS_TOKEN')
NO_REPLY_EMAIL = get_secret('NO_REPLY_EMAIL')

NOTIFICATION_LOG_PREFIX = 'EMAIL_NOTIFICATION'


#sa_private_key_b64 = get_secret(MODULE_API_PIPELINE_TASK_SERVICE_ACCOUNT_NAME)
#gls_service = authenticate_google_service(sa_private_key_b64, None, 'lifesciences', 'v2beta')
gls_service = discovery.build('lifesciences', 'v2beta', credentials=GoogleCredentials.get_application_default())

parent_id = f"projects/{GOOGLE_CLOUD_PROJECT_NUMBER}/locations/{GOOGLE_CLOUD_REGION}"


def get_operation_id_from_name(operation_name):
  try:
    return operation_name.rsplit('/', 1)[-1]
  except:
    logger.warn(f'Could not parse operation ID from operation_name "{operation_name}"')
    return operation_name


def start_pipeline(task_id, pipeline_request):
  req_body = get_json_from_class(pipeline_request)
  logger.debug(f'[TASK {task_id}] Starting Pipeline Request: {req_body}')

  try:
    request = gls_service.projects().locations().pipelines().run(parent=parent_id, body=req_body)
    response = request.execute()
    logger.debug(f'[TASK {task_id}] Pipeline Response: {response}')
    return response
  except Exception as err:
    logger.error(f"[TASK {task_id}] Pipeline Error: {err}")
    raise PipelineRunError(err)


def create_pipeline_operation_record(task, response):
  if response is None:
    raise PipelineRunError()

  name = response.get('name')
  metadata = response.get('metadata')
  if name is None or metadata is None:
    raise PipelineRunError(f'Pipeline start response missing expected properties (name = "{name}", metadata = "{metadata}")')

  id = get_operation_id_from_name(name)
  op = PipelineOperation(id)
  if op._exists:
    logger.warn(f'[CREATE {id}] PipelineOperation object with ID {id} already exists: {dict(op)}')

  op.set_properties(**{
    'id': id,
    'operation': name,
    'operation_kind': task.kind,
    'metadata': metadata,
    'report_path': None,
    'done': False,
    'error': False
  })
  op.save()
  return op


def get_pipeline_status(operation_name):
  """Return pipeline status
  Retrieves and returns the status for a pipeline
  Args:
    operation_name (string): The name of the operation
  Sample Args:
    operation_name = "projects/111111111111/locations/us-central1/operations/1111111111111111111"

  Return:
    {} (GlS Request Response)
  Sample Return:
    {
      done: true
    }
  """
  logger.debug(f'get_pipeline_status: operation_name:{operation_name}')
  request = gls_service.projects().locations().operations().get(name=operation_name)
  response = request.execute()

  id = get_operation_id_from_name(operation_name)
  logger.debug(f'[STATUS {id}] Pipeline status response: {response}')
  return response


def update_pipeline_operation_record(operation_name):
  logger.debug(f'update_pipeline_operation_record: operation_name:{operation_name}')
  id = get_operation_id_from_name(operation_name)

  try:
    status = get_pipeline_status(operation_name)
  except: 
    logger.warn(f"[UPDATE {id}] GLS Operation NOT FOUND")
    return

  op = PipelineOperation(id)
  if not op._exists:
    logger.warn(f'[UPDATE {id}] PipelineOperation entity with ID {id} not found.')
    return

  logger.info(f"[UPDATE {id}] Done = {status.get('done')}, Error = {status.get('error')}")
  op.set_properties(**{
    'done':  status.get('done'),
    'error': status.get('error'),
  })
  op.save()
  return op


def update_all_linked_status_records(kind, operation_name):
  logger.debug(f'update_all_linked_status_records: kind:{kind} operation_name:{operation_name}')
  op_id = get_operation_id_from_name(operation_name)

  status = get_pipeline_status(operation_name)
  done = status.get('done')
  error = status.get('error')
  if error:
    logger.error(f"[UPDATE {op_id}] Error: Kind: {kind} Operation Name: {operation_name} error: {error}")
  if done:
    status = TaskStatus.ERROR if error else TaskStatus.COMPLETE
  else:
    status = TaskStatus.RUNNING

  filters = [("operation_name", "=", operation_name)]
  ds_entities = query_ds_entities(kind, filters=filters, keys_only=True)
  for entity in ds_entities:
    if kind == DatabaseOperation.kind:
      status_record = DatabaseOperation(entity.key.name)
    elif kind == IndelPrimer.kind:
      status_record = IndelPrimer(entity.key.name)
    elif kind == NemascanMapping.kind:
      status_record = NemascanMapping(entity.key.name)
    elif kind == HeritabilityReport.kind:
      status_record = HeritabilityReport(entity.key.name)
    else:
      logger.warn(f"Unrecognized kind: {kind}")
      continue

    # Only send a notification if the report's status has not been updated yet
    # TODO: Should be able to remove kind check if all report notifications merged into one system
    should_send_notification = all([
      done,
      status_record['status'] not in [TaskStatus.COMPLETE, TaskStatus.ERROR],
      kind in [NemascanMapping.kind, HeritabilityReport.kind],
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
