import backoff
from googleapiclient.errors import HttpError

from caendr.services.logger import logger
from caendr.utils.env       import get_env_var

from pipelines.task_handler import DatabaseOperationTaskHandler, IndelFinderTaskHandler, HeritabilityTaskHandler, NemascanTaskHandler

from caendr.models.datastore             import Species
from caendr.models.error                 import APIBadRequestError, NotFoundError
from caendr.services.nemascan_mapping    import update_nemascan_mapping_status
from caendr.services.database_operation  import update_db_op_status
from caendr.services.indel_primer        import update_indel_primer_status
from caendr.services.heritability_report import update_heritability_report_status



# Get environment variables
DB_OPERATIONS_TASK_QUEUE_NAME = get_env_var('MODULE_DB_OPERATIONS_TASK_QUEUE_NAME')
INDEL_PRIMER_TASK_QUEUE_NAME  = get_env_var('INDEL_PRIMER_TASK_QUEUE_NAME')
HERITABILITY_TASK_QUEUE_NAME  = get_env_var('HERITABILITY_TASK_QUEUE_NAME')
NEMASCAN_TASK_QUEUE_NAME      = get_env_var('NEMASCAN_TASK_QUEUE_NAME')



def get_task_handler(queue_name, *args, **kwargs):
  mapping = {
    DB_OPERATIONS_TASK_QUEUE_NAME: DatabaseOperationTaskHandler,
    INDEL_PRIMER_TASK_QUEUE_NAME:  IndelFinderTaskHandler,
    HERITABILITY_TASK_QUEUE_NAME:  HeritabilityTaskHandler,
    NEMASCAN_TASK_QUEUE_NAME:      NemascanTaskHandler,
  }
  cls = mapping.get(queue_name, None)

  if cls is None:
    raise APIBadRequestError(f'Invalid task route {queue_name}')

  try:
    return cls(*args, **kwargs)

  except NotFoundError as ex:
    if ex.kind == Species.kind:
      raise APIBadRequestError(f'{ cls._Entity_Class.kind } task has invalid species value') from ex
    else:
      raise APIBadRequestError(f'Could not find { cls._Entity_Class.kind } object wih this ID') from ex



def start_job(payload, task_route, run_if_exists=False):
  '''
    Start a job on the given route.

    Args:
      - payload: The job payload.
      - task_route: The queue to run the job in.
      - run_if_exists (bool, optional): If True, will still run the job even if the specified job container exists. Default False.

    Returns:
      - handler (TaskHandler): A TaskHandler object of the subclass that handles the given task route, initialized with the given payload.
      - create_response: The response to the CloudRun create job request.
      - run_response:    The response to the CloudRun run job request.

    Raises:
      APIBadRequestError: The payload & task route do not identify an existing / valid Entity.
      HttpError: Forwarded from googleapiclient from create & run requests. If `run_if_exists` is True, ignores status code 409 from create request.
  '''
  task_id = payload.get('id', 'no-id')
  logger.info(f"[TASK {task_id}] Starting job in queue { task_route }. Payload: { payload }")


  # With exponential backoff, this is approx (2^(n-1))-1 = 127 sec, or a little over 2 minutes
  max_tries = 8

  def log_backoff(details):
    logger.warn(f'[TASK {task_id}] Failed to run job on attempt #{details["tries"]}/{max_tries} (time elapsed: {details["elapsed"]:00.1f}s). Trying again...')

  def log_giveup(details):
    logger.warn(f'[TASK {task_id}] Failed to run job on attempt #{details["tries"]}/{max_tries} (time elapsed: {details["elapsed"]:00.1f}s).')

  @backoff.on_exception(
      backoff.expo, HttpError, giveup=lambda ex: ex.status_code != 400, max_tries=max_tries, on_backoff=log_backoff, on_giveup=log_giveup, jitter=None
  )
  def _run_job(handler):
    return handler.run_job()


  # Try to create a task handler of the appropriate type
  handler = get_task_handler(task_route, **payload)

  # Create a CloudRun job for this task
  try:
    create_response = handler.create_job()

  # If the job already exists, optionally bail out
  except HttpError as ex:
    if run_if_exists and ex.status_code == 409:
      logger.warn(f'[TASK {task_id}] Encountered HttpError: {ex}')
      logger.warn(f'[TASK {task_id}] Running job again...')
      create_response = ex.resp
    else:
      raise

  # Run the CloudRun job
  run_response, pub_sub_id = _run_job(handler)

  # Return all computed values
  return handler, create_response, run_response



def update_status_safe(queue_name, op_id, call_id='', status=None, **kwargs):
  '''
    Safely update the TaskStatus of the given Entity.
    Logs & ignores errors.
  '''

  # Mapping of queues to status update functions
  MAPPING = {
    DB_OPERATIONS_TASK_QUEUE_NAME: update_db_op_status,
    INDEL_PRIMER_TASK_QUEUE_NAME:  update_indel_primer_status,
    HERITABILITY_TASK_QUEUE_NAME:  update_heritability_report_status,
    NEMASCAN_TASK_QUEUE_NAME:      update_nemascan_mapping_status,
  }

  # Try running the appropriate update function, forwarding any extra keywords
  try:
    # _update_status(queue_name, op_id, status=status, **kwargs)
    return MAPPING[queue_name](op_id, status=status, **kwargs)

  # If update failed, log the exception and ignore
  except Exception as ex:
    msg = f'Failed to update status to { status }: { ex }'
    if call_id:
      logger.error(f'[{ call_id }] { msg }')
    else:
      logger.error(msg)
