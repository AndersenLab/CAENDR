from   abc     import ABC, abstractmethod
import backoff
from   ssl     import SSLEOFError

from googleapiclient.errors import HttpError

from caendr.services.logger import logger
from caendr.utils.env       import get_env_var

from caendr.models.datastore            import DataJobEntity, PipelineOperation, Container
from caendr.models.error                import PipelineRunError, NotFoundError
from caendr.models.lifesciences         import ServiceAccount, VirtualMachine, Resources, Action, Pipeline, Request
from caendr.services.cloud.cloudrun     import create_job, run_job
from caendr.services.cloud.lifesciences import start_pipeline
from caendr.services.cloud.pubsub       import publish_message
from caendr.services.cloud.utils        import make_dns_name_safe



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


class Runner(ABC):
  '''
    Abstract class for running a job.

    As a general rule of thumb, Runner objects should be unique up to kind + data ID.
    For example, two jobs submitted by different users on the same data should (mostly) have equivalent GCPRunners.

    However, a single runner may represent multiple *executions* of the same job on the same data.
    In this case:
      - The `run` function should return a unique identifier for the execution that it started.
  '''

  # String identifying the type of job being run
  # Should correspond with the report kind
  @property
  @abstractmethod
  def kind(self) -> str: pass

  # String uniquely identifying the job itself
  # Runners with the same data_id are considered to be running the same "computation"
  # Individual runs of this data are available as executions, meaning the execution ID is required
  # to distinguish between multiple executions with the same data_id
  data_id: str

  # The report field to use as the data ID
  # Defaults to data hash, but may be overwritten in subclasses
  _data_id_field: str = 'data_hash'

  # Storage class to record metadata about an execution
  _Record_Class: None


  def __init__(self, data_id: str = None, report: DataJobEntity = None):
    '''
      Create a new Runner object.

      Takes one of two mutually exclusive arguments: the data ID directly, or a job report
      containing that data ID in the appropriate field.

      Arguments:
        - data_id (str):
            Unique identifier for the job data.
            Runners with the same data ID are considered to be running the same "computation".
        - report (DataJobEntity):
            Job report to initialize the runner from. Must have the same kind as the Runner subclass.
            Must contain the appropriate data ID field (defaults to "data_hash")

      Raises:
        - ValueError:
            The incorrect number of arguments was provided, or the report was invalid.
    '''

    # Arguments are mutually exclusive
    if not ((data_id is None) ^ (report is None)):
      raise ValueError('Either "data_id" should be provided, or "report" should be provided.')

    # If report provided, validate its kind and extract the data ID from it
    if report is not None:
      if report.kind != self.kind:
        raise ValueError(f'Cannot initialize runner of kind {self.kind} from report with kind {report.kind}')
      data_id = getattr(report, self._data_id_field)
      if data_id is None:
        raise ValueError(f'Cannot initialize runner of kind {self.kind} from report with no "{self._data_id_field}" field')

    # Set the data ID
    self.data_id = data_id


  @abstractmethod
  def run(self, report: DataJobEntity, run_if_exists: bool = False) -> str:
    '''
      Start a job to compute the given report.

      Args:
        - run_if_exists (bool, optional): If True, will still run the job even if the specified job container exists. Default False.

      Returns:
        An identifier for the execution that was created.  Will be unique within this Runner object.
    '''
    pass



class LocalRunner(Runner):
  '''
    Template class for a job that runs locally, without needing to start a container.
  '''
  pass



class GCPRunner(Runner):
  '''
    Template class for running a job in GCP.

    Individual GCPRunner objects should be unique up to data ID.
    For example, two jobs submitted by different users with the same data ID will have equivalent GCPRunners.
    By default, the data ID is taken to be the data_hash.

    Introduces new abstract methods for starting a GCP service.
  '''

  _Record_Class = PipelineOperation

  # Machine Parameters #
  # Can be overwritten in subclasses as needed
  _MACHINE_TYPE                  = 'n1-standard-1'
  _PREEMPTIBLE                   = False
  _BOOT_IMAGE                    = 'projects/cos-cloud/global/images/family/cos-stable'
  _BOOT_DISK_SIZE_GB             = 20
  _ENABLE_STACKDRIVER_MONITORING = True
  _VOLUME_NAME                   = 'nf-pipeline-work'

  # CloudRun Parameters #
  # Can be overwritten in subclasses as needed
  _TASK_COUNT    = 1
  _MAX_RETRIES   = 1
  _MEMORY_LIMITS = { 'memory': '512Mi', 'cpu': '1' }


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


  # Lookup Function #

  def get(self, key, default=None):
    return getattr(self, f'_{key}', default)


  # Container Environment #

  def get_gcp_vars(self):
    return {
      "GOOGLE_SERVICE_ACCOUNT_EMAIL": sa_email,
      "GOOGLE_PROJECT":               GOOGLE_CLOUD_PROJECT_ID,
      "GOOGLE_ZONE":                  GOOGLE_CLOUD_ZONE,
    }
  
  def get_data_job_vars(self, report: DataJobEntity):
    return {
      "TRAIT_FILE": f"gs://{ report.get_bucket_name() }/{ report.get_data_blob_path() }",
      "WORK_DIR":   f"gs://{ WORK_BUCKET_NAME         }/{ report.data_hash }",
      "DATA_DIR":   report.get_data_directory(),
      "OUTPUT_DIR": f"gs://{ report.get_bucket_name() }/{ report.get_result_path() }",
    }

  @abstractmethod
  def construct_environment(self, report: DataJobEntity) -> dict:
    '''
      Construct the set of environment variables for the container as a dictionary.
      Output should map variable names to values.
    '''
    pass


  # Container Command #

  @abstractmethod
  def construct_command(self, report: DataJobEntity) -> list:
    '''
      Construct the command used to start the container functionality.
      Output should be a list of individual terms used in the command line.
    '''
    pass


  def _create_execution_record(self, execution_id, response):
    '''
      Create a PipelineOperation record object to track a specific execution of this job.
    '''
    if response is None:
      raise PipelineRunError(f'No response provided for execution {execution_id}')

    # Validate response properties
    try:
      name = response.get('response').get('name')
    except:
      name = response.get('name')
    metadata = response.get('metadata')
    if name is None or metadata is None:
      raise PipelineRunError(f'Pipeline start response missing expected properties (name = "{name}", metadata = "{metadata}")')


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


  #
  # Names
  #

  @property
  def operation_name(self):
    return f'{ super().operation_name }/jobs/{ self.job_name }'

  def _get_execution_name(self, execution_id):
    return f'{ self.operation_name }/executions/{ self.job_name }-{ execution_id }'


  #
  # Backoff Logging Functions
  #

  @staticmethod
  def _get_id_from_details(details):
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
  def run(self, report, run_if_exists=False):
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
        APIBadRequestError: The payload & task route do not identify an existing / valid Entity.
        HttpError: Forwarded from googleapiclient from create & run requests. If `run_if_exists` is True, ignores status code 409 from create request.
        PipelineRunError: A PipelineOperation record could not be created for this execution
    '''

    # Create a CloudRun job for this task
    try:
      create_response = self._create(report)

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

    # If a known error occurred creating the record, raise it as-is
    except PipelineRunError:
      raise

    # If a generic exception occurred, wrap it in a PipelineRun error so the caller knows what stage of the function it came from
    except Exception as ex:
      raise PipelineRunError(f'Failed to create Pipeline Operation record for execution {exec_id}') from ex

    # Return the ID of the execution that was just started
    return exec_id


  #
  # Creating & Running CloudRun Job
  #

  def _create(self, report: DataJobEntity):
    '''
      Create a CloudRun Job to run this task.
    '''
    return create_job(**{
      'name':        self.job_name,
      'task_count':  self.get('TASK_COUNT'),
      'timeout':     self.get('TIMEOUT'),
      'max_retries': self.get('MAX_RETRIES'),

      'container': {
        'image':     report.get_container().uri(),
        'name':      self.job_name, # Name of the container specified as a DNS_LABEL (RFC 1123).

        # Startup Command
        'args':      self.construct_command(report)[1:],
        'command':   self.construct_command(report)[0:1],

        # Environment
        'env': [
          { 'name': name, 'value': value } for name, value in self.construct_environment(report).items()
        ],

        # Compute Resources
        'resources': {
          'limits': self.get('MEMORY_LIMITS'),
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
