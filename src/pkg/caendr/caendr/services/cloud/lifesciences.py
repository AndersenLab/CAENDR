import os

from caendr.services.logger import logger
from googleapiclient import discovery
from oauth2client.client import GoogleCredentials

from caendr.models.datastore import PipelineOperation, HeritabilityReport, NemascanMapping, get_entity_by_kind
from caendr.models.error import PipelineRunError, NotFoundError
from caendr.models.task import TaskStatus
from caendr.services.cloud.datastore import query_ds_entities
from caendr.services.cloud.service_account import authenticate_google_service
from caendr.utils.env import get_env_var
from caendr.utils.json import get_json_from_class


GOOGLE_CLOUD_PROJECT_NUMBER = os.environ.get('GOOGLE_CLOUD_PROJECT_NUMBER')
GOOGLE_CLOUD_REGION = os.environ.get('GOOGLE_CLOUD_REGION')
MODULE_API_PIPELINE_TASK_SERVICE_ACCOUNT_NAME = os.environ.get('MODULE_API_PIPELINE_TASK_SERVICE_ACCOUNT_NAME')


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

  try:
    name = response.get('response').get('name')
  except:
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
  return {
    'response': response,
    'done':     response.get('done', False),
    'error':    response.get('error', False),
  }


def update_all_linked_status_records(kind, operation_name):

  # TODO: This entire function should move to "utils", since it's agnostic to pipeline type
  #       This would get rid of the local import.
  from caendr.services.cloud.utils import get_operation_status, send_result_email

  logger.debug(f'update_all_linked_status_records: kind:{kind} operation_name:{operation_name}')

  status, service, op_id = get_operation_status(operation_name)
  done = status.get('done')
  error = status.get('error')

  if error:
    logger.error(f"[UPDATE {op_id}] Error: Kind: {kind} Operation Name: {operation_name} error: {error}")
  if done:
    status = TaskStatus.ERROR if error else TaskStatus.COMPLETE
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

