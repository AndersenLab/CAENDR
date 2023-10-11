import backoff
from googleapiclient.errors import HttpError
from ssl import SSLEOFError

from caendr.services.logger import logger
from caendr.utils.env       import get_env_var

from caendr.models.datastore             import Species
from caendr.models.error                 import APIBadRequestError, NotFoundError
from caendr.services.nemascan_mapping    import update_nemascan_mapping_status
from caendr.services.database_operation  import update_db_op_status
from caendr.services.indel_primer        import update_indel_primer_status
from caendr.services.heritability_report import update_heritability_report_status
from caendr.models.job_pipeline          import DatabaseOperationPipeline, IndelFinderPipeline, HeritabilityPipeline, NemascanPipeline



# Get environment variables
DB_OPERATIONS_TASK_QUEUE_NAME = get_env_var('MODULE_DB_OPERATIONS_TASK_QUEUE_NAME')
INDEL_PRIMER_TASK_QUEUE_NAME  = get_env_var('INDEL_PRIMER_TASK_QUEUE_NAME')
HERITABILITY_TASK_QUEUE_NAME  = get_env_var('HERITABILITY_TASK_QUEUE_NAME')
NEMASCAN_TASK_QUEUE_NAME      = get_env_var('NEMASCAN_TASK_QUEUE_NAME')



def log_ssl_backoff(details):
  logger.warn(f'[TASK {details["args"][0].get("id", "no-id")}] Encountered SSLEOFError trying to start job. Trying again in {details["wait"]:00.1f}s...')

def log_ssl_giveup(details):
  logger.warn(f'[TASK {details["args"][0].get("id", "no-id")}] Encountered SSLEOFError trying to start job. Giving up. Total time elapsed: {details["elapsed"]:00.1f}s.')



def get_task_handler(queue_name, *args, **kwargs):
  '''
    Args:
      - queue_name: The queue to run the job in.
      - kwargs: The job payload.
  '''
  mapping = {
    DB_OPERATIONS_TASK_QUEUE_NAME: DatabaseOperationPipeline,
    INDEL_PRIMER_TASK_QUEUE_NAME:  IndelFinderPipeline,
    HERITABILITY_TASK_QUEUE_NAME:  HeritabilityPipeline,
    NEMASCAN_TASK_QUEUE_NAME:      NemascanPipeline,
  }
  cls = mapping.get(queue_name, None)

  if cls is None:
    raise APIBadRequestError(f'Invalid task route {queue_name}')

  try:
    return cls.lookup(kwargs['id'])

  except NotFoundError as ex:
    if ex.kind == Species.kind:
      raise APIBadRequestError(f'{ cls.get_kind() } task has invalid species value') from ex
    else:
      raise APIBadRequestError(f'Could not find { cls.get_kind() } object wih this ID') from ex



@backoff.on_exception(
    backoff.constant, SSLEOFError, max_tries=3, interval=20, jitter=None, on_backoff=log_ssl_backoff, on_giveup=log_ssl_giveup,
)
def start_job(handler, run_if_exists=False):
  '''
    Start a job on the given route.

    On encountering an SSL EOF error, will wait 20s and try again, up to 3 times total.
    This should help ensure the job runs even if an existing connection has gone stale.

    Args:
      - handler (JobPipeline): A JobPipeline object of the subclass that handles the given task route, initialized with the given payload.
      - run_if_exists (bool, optional): If True, will still run the job even if the specified job container exists. Default False.

    Returns:
      A dictionary of responses generated in starting the job:
        - create: The response to the CloudRun create job request.
        - run:    The response to the CloudRun run job request.

    Raises:
      APIBadRequestError: The payload & task route do not identify an existing / valid Entity.
      HttpError: Forwarded from googleapiclient from create & run requests. If `run_if_exists` is True, ignores status code 409 from create request.
  '''

  # With exponential backoff, this is approx (2^(n-1))-1 = 127 sec, or a little over 2 minutes
  max_tries = 8

  def log_backoff(details):
    logger.warn(f'[TASK {handler.report.id}] Failed to run job on attempt {details["tries"]}/{max_tries}. Trying again in {details["wait"]:00.1f}s...')

  def log_giveup(details):
    logger.warn(f'[TASK {handler.report.id}] Failed to run job on attempt {details["tries"]}/{max_tries}. Total time elapsed: {details["elapsed"]:00.1f}s.')

  # Local helper function to ensure job is started
  # There is a delay between when the job "create" request is sent and when the job becomes available for "run",
  # so we use exponential backoff to wait for the job to finish being created
  @backoff.on_exception(
      backoff.expo, HttpError, giveup=lambda ex: ex.status_code != 400, max_tries=max_tries, on_backoff=log_backoff, on_giveup=log_giveup, jitter=None
  )
  def _run_job(handler):
    return handler.run_job()


  # Create a CloudRun job for this task
  try:
    create_response = handler.create_job()

  # If the job already exists, optionally bail out
  except HttpError as ex:
    if run_if_exists and ex.status_code == 409:
      logger.warn(f'[TASK {handler.report.id}] Encountered HttpError: {ex}')
      logger.warn(f'[TASK {handler.report.id}] Running job again...')
      create_response = ex.resp
    else:
      raise

  # Run the CloudRun job
  run_response, pub_sub_id = _run_job(handler)

  # Return the individual responses
  return { 'create': create_response, 'run': run_response }



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
