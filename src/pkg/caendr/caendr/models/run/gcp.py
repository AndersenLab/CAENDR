from   abc     import ABC, abstractmethod
import backoff
from   ssl     import SSLEOFError
from   typing  import Optional

# Parent class
from .base import Runner

from googleapiclient.errors import HttpError

from caendr.services.logger import logger
from caendr.utils.env       import get_env_var

from caendr.models.datastore            import PipelineOperation, DatabaseOperation
from caendr.models.error                import PipelineRunError, NotFoundError
from caendr.models.report               import GCPReport
from caendr.models.sql                  import DbOp
from caendr.models.status               import JobStatus
from caendr.models.lifesciences         import ServiceAccount, VirtualMachine, Resources, Action, Pipeline, Request
from caendr.services.cloud.cloudrun     import create_job, run_job, get_job_execution_status
from caendr.services.cloud.lifesciences import start_pipeline, get_pipeline_status
from caendr.services.cloud.pubsub       import publish_message
from caendr.services.cloud.utils        import make_dns_name_safe, parse_operation_name



# Project Environment Variables
GOOGLE_CLOUD_PROJECT_NUMBER = get_env_var('GOOGLE_CLOUD_PROJECT_NUMBER')
GOOGLE_CLOUD_PROJECT_ID     = get_env_var('GOOGLE_CLOUD_PROJECT_ID')
GOOGLE_CLOUD_REGION         = get_env_var('GOOGLE_CLOUD_REGION')
GOOGLE_CLOUD_ZONE           = get_env_var('GOOGLE_CLOUD_ZONE')

# Module Environment Variables
SERVICE_ACCOUNT_NAME        = get_env_var('MODULE_API_PIPELINE_TASK_SERVICE_ACCOUNT_NAME')
PUB_SUB_TOPIC_NAME          = get_env_var('MODULE_API_PIPELINE_TASK_PUB_SUB_TOPIC_NAME')
WORK_BUCKET_NAME            = get_env_var("MODULE_API_PIPELINE_TASK_WORK_BUCKET_NAME")
DATA_BUCKET_NAME            = get_env_var("MODULE_API_PIPELINE_TASK_DATA_BUCKET_NAME")

# Service Account & Pub/Sub Info
sa_email = f"{SERVICE_ACCOUNT_NAME}@{GOOGLE_CLOUD_PROJECT_ID}.iam.gserviceaccount.com"
pub_sub_topic = f'projects/{GOOGLE_CLOUD_PROJECT_ID}/topics/{PUB_SUB_TOPIC_NAME}'
SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]

ZONE = 'us-central1-a'
LOCAL_WORK_PATH = '/workdir'

parent_id = f"projects/{GOOGLE_CLOUD_PROJECT_NUMBER}/locations/{GOOGLE_CLOUD_REGION}"



class GCPRunner(Runner):
  '''
    Template class for running a job in GCP.

    Individual GCPRunner objects should be unique up to data ID.
    For example, two jobs submitted by different users with the same data ID will have equivalent GCPRunners.
    By default, the data ID is taken to be the data_hash.

    Introduces new abstract methods for starting a GCP service.
  '''

  _Record_Class = PipelineOperation


  # Creation #

  # TODO: Can we make kind optional?
  @classmethod
  def from_operation_name(cls, kind, operation_name: str):
    '''
      Create a Runner of this class from the given GCP operation name.
      Raises an error if the operation name does not specify a job with the same kind as this class.

      Arguments:
        - operation_name (str): The GCP operation name for the job.

      Returns:
        A Runner of the given subclass representing this operation.

      Raises:
        - ValueError: The given operation name is not valid for this subclass.
    '''

    # Parse the operation name into a dictionary
    op_name_fields = parse_operation_name(operation_name)

    # Split the job name into the kind and data ID
    _kind, data_id = cls.split_job_name( kind, op_name_fields['jobs'] )

    if _kind != make_dns_name_safe(kind):
      raise ValueError(f'Cannot initialize runner subclass {cls.__name__} with kind {kind} from operation with kind {_kind} (full name: {operation_name})')

    return cls(kind, data_id)


  # Name Properties #

  @property
  @abstractmethod
  def operation_name(self):
    '''
      The name of this job in GCP.
    '''
    return parent_id

  @property
  def job_name(self) -> str:
    '''
      A unique name for this job, specified as a DNS_LABEL (RFC 1123).
      Will be used to name any container running this job.

      Unique up to data ID, i.e. JobPipeline objects which represent the same data
      submitted by different users will have the SAME job name.

      The resulting name should comply with the DNS_LABEL name format:
        - May only contain alphanumeric characters & hyphens
        - Must start with a letter
        - Must not end with a hyphen
        - May be at most 64 characters long
    '''
    return make_dns_name_safe( f'{self.kind}-{self.data_id}' )

  # TODO: Handle the DbOp case more gracefully
  @classmethod
  def split_job_name(cls, kind, job_name) -> (str, str):
    '''
      Convert a job name into a kind and data ID.

      NOTE: This implementation assumes that the data ID cannot have any hyphens.
            If the data ID for a given job type can include hyphens,
            this function must be overwritten in the appropriate subclass.

      Arguments:
        - job_name (str): The name of the job to parse

      Returns:
        - kind (str): The kind of the job specified by the given name
        - data_id (str): The data ID of the job specified by the given name

      Raises:
        - ValueError: The given name was not valid for this job type.
    '''

    # Make sure job name starts with the correct prefix, based on the provided kind
    target_prefix = make_dns_name_safe(kind) + '-'
    if not job_name.startswith(target_prefix):
      raise ValueError(f'Job name { job_name } does not start with the expected kind prefix "{ target_prefix }".')

    if kind != DatabaseOperation.kind:
      _kind, data_id = job_name.rsplit('-', 1)
      if _kind != make_dns_name_safe(kind):
        raise ValueError(f'Job name { job_name } does not start with the expected kind prefix "{ make_dns_name_safe(kind) }".')
      return _kind, data_id

    # Treat the rest of the job name as the data ID
    data_id = job_name[ len(target_prefix) :]

    # Loop through valid database operations
    for op in DbOp:
      if data_id == make_dns_name_safe(op.name):
        return make_dns_name_safe(kind), op.name

    raise ValueError(f'Job name { job_name } does not match any valid database operations (searching for: "{ data_id }").')


  # Container Environment #

  @classmethod
  def default_environment(cls):
    return {
      "GOOGLE_SERVICE_ACCOUNT_EMAIL": sa_email,
      "GOOGLE_PROJECT":               GOOGLE_CLOUD_PROJECT_ID,
      "GOOGLE_ZONE":                  GOOGLE_CLOUD_ZONE,
    }


  # Execution Record #

  def _create_execution_record(self, execution_id, response):
    '''
      Create a PipelineOperation record object to track a specific execution of this job.
    '''
    if response is None:
      raise ValueError(f'No response provided for execution {execution_id}')

    # Validate response properties
    try:
      name = response.get('response').get('name')
    except:
      name = response.get('name')
    metadata = response.get('metadata')
    if name is None or metadata is None:
      raise ValueError(f'Pipeline start response missing expected properties (name = "{name}", metadata = "{metadata}")')


    id = f'{ self.job_name }-{ execution_id }'
    op = self._Record_Class(id)
    if op._exists:
      logger.warn(f'[CREATE {id}] Execution record object ({self._Record_Class.kind}) with ID {id} already exists: {dict(op)}')

    op.set_properties(**{
      'id':             id,
      'operation':      name,
      'operation_kind': self.kind,
      'execution_id':   execution_id,
      'metadata':       metadata,
      'report_path':    None,
      'done':           False,
      'error':          False,
    })
    op.save()
    return op


  def _lookup_execution_record(self, execution_id):
    id = f'{ self.job_name }-{ execution_id }'
    op = self._Record_Class(id)
    if not op._exists:
      raise NotFoundError(self._Record_Class, {'id': id})
    return op


  # TODO: This is defined a bit awkwardly for backwards-compatability...
  #       Older jobs were run in Lifesciences, and do not have an explicit execution ID available in their records
  #       Maybe the PipelineOperation record needs to track which runner was used? Or maybe we just lookup by operation name by default?
  #       On the bright side, defining this function at the GCPRunner level lets the Job Pipeline look up the operation record
  #       without needing to know what Runner was used
  def get_err_msg(self, execution_id: str = None, operation_name: str = None) -> Optional[str]:

    # Make sure arguments are mutually exclusive
    if not ((execution_id is None) ^ (operation_name is None)):
      raise ValueError(f'Exactly one of "execution_id" and "operation_name" should be defined.')

    # Find the record based on execution ID
    if execution_id is not None:

      # If this execution is not in the ERROR state, return None
      if self.check_status(execution_id) is not JobStatus.ERROR:
        return None

      # Lookup the execution record for the given ID
      record = self._lookup_execution_record(execution_id)

    # Find the record based on operation name
    else:
      record = self._Record_Class( operation_name.split('/').pop() )

    # Return the error field from the record object
    return record['error']



class GCPCloudRunRunner(GCPRunner):
  '''
    Template class for running a job in GCP CloudRun.

    Provides CloudRun-specific implementations of create_job and run_job
    that rely on the new abstract methods introduced by GCPRunner.
  '''

  # Total number of times to try creating & running the CloudRun Job if an SSLEOFError is encountered
  _MAX_TRIES_TOTAL = 3

  # Total number of times to try running the CloudRun Job after it has been created
  # With exponential backoff, this is approx (2^(n-1))-1 = 127 sec, or a little over 2 minutes
  _MAX_TRIES_RUN   = 8


  # CloudRun Parameters #
  # Can be overwritten in subclasses as needed

  @classmethod
  def default_run_params(cls):
    return {
      **super().default_run_params(),
      'TASK_COUNT':    1,
      'MAX_RETRIES':   1,
      'MEMORY_LIMITS': { 'memory': '512Mi', 'cpu': '1' },
    }


  #
  # Names
  #

  @property
  def operation_name(self):
    return f'{ super().operation_name }/jobs/{ self.job_name }'

  def get_full_execution_name(self, execution_id: str) -> str:
    return f'{ self.operation_name }/executions/{ self.job_name }-{ execution_id }'

  def get_execution_id_from_operation_name(self, operation_name):
    try:
      exec_name = parse_operation_name(operation_name)['executions']
    except KeyError:
      raise ValueError(f'Operation name "{operation_name}" does not identify an execution')

    return exec_name.split('-')[-1]


  #
  # Status
  #

  def check_status(self, execution_id: str) -> JobStatus:
    '''
      Get the status of a specific execution of this job.

      Attempts to update the corresponding PipelineOperation record object with the new status.
    '''

    # Check the status of the job in GCP
    op_id = self.get_full_execution_name(execution_id)
    status = get_job_execution_status(op_id)

    # Try looking up and updating the pipeline operation record
    try:
      op = self._lookup_execution_record(execution_id)

      # Update the record object
      logger.info(f"[UPDATE {self.operation_name}] Done = {status.get('done')}, Error = {status.get('error')}")
      op.set_properties(**{
        'done':  status.get('done'),
        'error': status.get('error'),
      })
      op.save()

    # If not found, log and move on
    except NotFoundError as ex:
      logger.error(f'[UPDATE {self.operation_name}] Could not find pipeline operation record { op_id }: { ex }')

    # If CloudRun status is error or done, return corresponding JobStatus values
    if status.get('error'):
      return JobStatus.ERROR
    elif status.get('done'):
      return JobStatus.COMPLETE

    # Otherwise, job is still running
    return JobStatus.RUNNING


  #
  # Backoff Logging Functions
  #

  @staticmethod
  def _get_id_from_details(details):
    # Since all backoff logging functions are run on methods, the first argument will be `self`.
    return details['args'][0].job_name

  @staticmethod
  def _log_ssl_backoff(details):
    logger.warn(f'[RUN { GCPCloudRunRunner._get_id_from_details(details) }] Encountered SSLEOFError trying to start job. Trying again in {details["wait"]:00.1f}s...')

  @staticmethod
  def _log_ssl_giveup(details):
    logger.warn(f'[RUN { GCPCloudRunRunner._get_id_from_details(details) }] Encountered SSLEOFError trying to start job. Giving up. Total time elapsed: {details["elapsed"]:00.1f}s.')

  @staticmethod
  def _log_backoff(details):
    logger.warn(f'[RUN { GCPCloudRunRunner._get_id_from_details(details) }] Failed to run job on attempt {details["tries"]}/{GCPCloudRunRunner._MAX_TRIES_RUN}. Trying again in {details["wait"]:00.1f}s...')

  @staticmethod
  def _log_giveup(details):
    logger.warn(f'[RUN { GCPCloudRunRunner._get_id_from_details(details) }] Failed to run job on attempt {details["tries"]}/{GCPCloudRunRunner._MAX_TRIES_RUN}. Total time elapsed: {details["elapsed"]:00.1f}s.')


  #
  # Main Run Function
  #

  @backoff.on_exception(
      backoff.constant, SSLEOFError, max_tries=_MAX_TRIES_TOTAL, interval=20, jitter=None, on_backoff=_log_ssl_backoff.__func__, on_giveup=_log_ssl_giveup.__func__,
  )
  def run(self, command: list, env: dict, container_uri: str, params: dict, run_if_exists: bool = False) -> str:
    '''
      Start a job on the given route.

      On encountering an SSL EOF error, will wait 20s and try again, up to 3 times total.
      This should help ensure the job runs even if an existing connection has gone stale.

      Args:
        - handler (JobPipeline): A JobPipeline object of the subclass that handles the given task route, initialized with the given payload.
        - run_if_exists (bool, optional): If True, will still run the job even if the specified job container exists. Default False.

      Returns:
        A unique ID for the execution started by this call. This can be used to check the status of that execution.

      Raises:
        HttpError: Forwarded from googleapiclient from create & run requests. If `run_if_exists` is True, ignores status code 409 from create request.
        PipelineRunError: A PipelineOperation record could not be created for this execution.
        ValueError: The given report is invalid.
    '''

    # Create a CloudRun job for this task
    try:
      create_response = self._create(command, env, container_uri, params)

    # If the job already exists, optionally bail out
    except HttpError as ex:
      if run_if_exists and ex.status_code == 409:
        logger.warn(f'[TASK {self.job_name}] Encountered HttpError: {ex}')
        logger.warn(f'[TASK {self.job_name}] Running job again...')
        create_response = ex.resp
      else:
        raise

    # Run the CloudRun job
    run_response, pub_sub_id = self._run()

    # Get the specific execution ID from the response
    exec_id = run_response['metadata']['name'].rsplit('-')[-1]

    # Create a PipelineOperation record to represent this execution
    try:
      self._create_execution_record(exec_id, run_response)

    # If a generic exception occurred, wrap it in a PipelineRun error so the caller knows what stage of the function it came from
    except Exception as ex:
      raise PipelineRunError(f'Failed to create Pipeline Operation record for execution {exec_id}') from ex

    # Return the ID of the execution that was just started
    return exec_id


  #
  # Creating & Running CloudRun Job
  #

  def _create(self, command: list, env: dict, container_uri: str, params: dict):
    '''
      Create a CloudRun Job to run this task.
    '''
    return create_job(**{
      'name':        self.job_name,
      'task_count':  params.get('TASK_COUNT'),
      'timeout':     params.get('TIMEOUT'),
      'max_retries': params.get('MAX_RETRIES'),

      'container': {
        'image':     container_uri,
        'name':      self.job_name, # Name of the container specified as a DNS_LABEL (RFC 1123).

        # Startup Command
        'args':      command[1:],
        'command':   command[0:1],

        # Environment
        'env': [
          { 'name': name, 'value': value } for name, value in env.items()
        ],

        # Compute Resources
        'resources': {
          'limits': params.get('MEMORY_LIMITS'),
          'startupCpuBoost': False,
        },
      }
    })


  # There is a delay between when the job "create" request is sent and when the job becomes available for "run",
  # so we use exponential backoff to wait for the job to finish being created
  @backoff.on_exception(
      backoff.expo, HttpError, giveup=lambda ex: ex.status_code != 400, max_tries=_MAX_TRIES_RUN, on_backoff=_log_backoff.__func__, on_giveup=_log_giveup.__func__, jitter=None
  )
  def _run(self):
    '''
      Initiate the CloudRun Job associated with this task.
    '''
    response = run_job(self.job_name)

    # Publish a Pub/Sub message to periodically check this job's status
    pub_sub_id = None
    try:
      pub_sub_id = publish_message(PUB_SUB_TOPIC_NAME, operation=response['metadata']['name'])
    except Exception as ex:
      logger.error(f'Could not publish Pub/Sub message for job {self.job_name}: {ex}')

    return response, pub_sub_id




class GCPLifesciencesRunner(GCPRunner):
  '''
    Template class for running a job in GCP Lifesciences.

    Provides Lifesciences-specific implementations of create_job and run_job
    that rely on the new abstract methods introduced by GCPRunner.

    Deprecated.
  '''

  # Machine Parameters #
  # Can be overwritten in subclasses as needed
  _MACHINE_TYPE                  = 'n1-standard-1'
  _PREEMPTIBLE                   = False
  _BOOT_IMAGE                    = 'projects/cos-cloud/global/images/family/cos-stable'
  _BOOT_DISK_SIZE_GB             = 20
  _ENABLE_STACKDRIVER_MONITORING = True
  _VOLUME_NAME                   = 'nf-pipeline-work'


  # def check_status(self):
  #   return get_pipeline_status(self.operation_name)

  def run(self, report, run_if_exists=False):
    '''
      Create and run a VM for this task using Lifesciences.
    '''

    # Resources
    virtual_machine = VirtualMachine(
      machine_type                   = self.get('MACHINE_TYPE'),
      preemptible                    = self.get('PREEMPTIBLE'),
      boot_disk_size_gb              = self.get('BOOT_DISK_SIZE_GB'),
      boot_image                     = self.get('BOOT_IMAGE'),
      enable_stackdriver_monitoring  = self.get('ENABLE_STACKDRIVER_MONITORING'),
      service_account                = ServiceAccount(email=sa_email, scopes=SCOPES),
    )
    resources = Resources(virtual_machine=virtual_machine, zones=[ZONE])

    # Action
    action = Action(
      always_run                     = False,
      block_external_network         = False,
      commands                       = self.construct_command(report),
      job_name                       = self.job_name,
      disable_image_prefetch         = False,
      disable_standard_error_capture = False,
      enable_fuse                    = False,
      environment                    = self.construct_environment(report),
      ignore_exit_status             = False,
      image_uri                      = report.get_container().uri(),
      publish_exposed_ports          = False,
      run_in_background              = False,
      timeout                        = self.get('TIMEOUT'),
    )

    # Pipeline Request
    pipeline = Pipeline( actions=[action], resources=resources, timeout=self.get('TIMEOUT') )
    pipeline_req = Request( pipeline=pipeline, pub_sub_topic=pub_sub_topic )

    # Start the pipeline
    # TODO: We don't have access to the task ID anymore...?
    response = start_pipeline(self.task.id, pipeline_req)

    # Would have to get an execution ID from the response
    return None
