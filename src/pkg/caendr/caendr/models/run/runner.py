from   abc     import ABC, abstractmethod
import backoff
from   ssl     import SSLEOFError

from googleapiclient.errors import HttpError

from caendr.services.logger import logger
from caendr.utils.env       import get_env_var

from caendr.models.datastore            import DataJobEntity, Species
from caendr.models.lifesciences         import ServiceAccount, VirtualMachine, Resources, Action, Pipeline, Request
from caendr.services.cloud.cloudrun     import create_job, run_job
from caendr.services.cloud.lifesciences import start_pipeline
from caendr.services.cloud.pubsub       import publish_message



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



class Runner(ABC):
  '''
    Abstract class for running a job.
  '''

  # TODO: Abstract away from storing report directly...
  report: DataJobEntity

  def __init__(self, report):
    self.report = report

  @abstractmethod
  def run(self, run_if_exists=False):
    '''
      Start a job on the given route.

      Args:
        - run_if_exists (bool, optional): If True, will still run the job even if the specified job container exists. Default False.

      Returns:
        A dictionary of responses generated in starting the job:
          - create: The response to the CloudRun create job request.
          - run:    The response to the CloudRun run job request.
    '''
    pass


  # TODO: This is pretty implementation-specific...
  @property
  def latest_release(self):
    return Species.get(self.report.species)['release_latest']



class LocalRunner(Runner):
  '''
    Template class for a job that runs locally, without needing to start a container.
  '''
  pass



class GCPRunner(Runner):
  '''
    Template class for running a job in GCP.

    Introduces new abstract methods for starting a GCP service..
  '''

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


  # Container Properties #
  # TODO: These overlap with JobPipeline -- as part of removing report var, should find a way to rewrite these

  @property
  def image_uri(self) -> str:
    '''
      The URI for this job's container image. Used to look up & create the container.
    '''
    return self.report.get_container().uri()

  @property
  def image_version(self) -> str:
    '''
      The version of this job's container image.
    '''
    return self.report.container_version

  @property
  def container_name(self) -> str:
    '''
      A unique name for a container computing this job.

      Unique up to data hash, i.e. JobPipeline objects which represent the same data
      submitted by different users will have DIFFERENT `container_name`s.
    '''
    return f'{self.report.kind}-{self.report.id}'.lower().replace('_', '-')
  
  @property
  def job_name(self):
    '''
      A unique name for a container computing the results of this job's input data.

      Unique up to data hash, i.e. JobPipeline objects which represent the same data
      submitted by different users will have the SAME job_name.
    '''
    return f'{self.report.kind}-{self.report.data_hash}'.lower().replace('_', '-')


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
  
  def get_data_job_vars(self):
    return {
      "TRAIT_FILE": f"gs://{ self.report.get_bucket_name() }/{ self.report.get_data_blob_path() }",
      "WORK_DIR":   f"gs://{ WORK_BUCKET_NAME              }/{ self.report.data_hash }",
      "DATA_DIR":   self.report.get_data_directory(),
      "OUTPUT_DIR": f"gs://{ self.report.get_bucket_name() }/{ self.report.get_result_path() }",
    }

  @abstractmethod
  def construct_environment(self, report) -> dict:
    '''
      Construct the set of environment variables for the container as a dictionary.
      Output should map variable names to values.
    '''
    pass


  # Container Command #

  @abstractmethod
  def construct_command(self, report) -> list:
    '''
      Construct the command used to start the container functionality.
      Output should be a list of individual terms used in the command line.
    '''
    pass



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
  # Backoff Logging Functions
  #

  @staticmethod
  def _get_id_from_details(details):
    return details['args'][0].get('report', {}).get('id', 'no-id')

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
  def run(self, run_if_exists=False):
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

    # Create a CloudRun job for this task
    try:
      create_response = self._create()

    # If the job already exists, optionally bail out
    except HttpError as ex:
      if run_if_exists and ex.status_code == 409:
        logger.warn(f'[TASK {self.report.id}] Encountered HttpError: {ex}')
        logger.warn(f'[TASK {self.report.id}] Running job again...')
        create_response = ex.resp
      else:
        raise

    # Run the CloudRun job
    run_response, pub_sub_id = self._run()

    # Return the individual responses
    return { 'create': create_response, 'run': run_response }


  #
  # Creating & Running CloudRun Job
  #

  def _create(self):
    '''
      Create a CloudRun Job to run this task.
    '''
    return create_job(**{
      'name':        self.job_name,
      'task_count':  self.get('TASK_COUNT'),
      'timeout':     self.get('TIMEOUT'),
      'max_retries': self.get('MAX_RETRIES'),

      'container': {
        'image':     self.image_uri,
        'name':      self.container_name, # Name of the container specified as a DNS_LABEL (RFC 1123).

        # Startup Command
        'args':      self.construct_command()[1:],
        'command':   self.construct_command()[0:1],

        # Environment
        'env': [
          { 'name': name, 'value': value } for name, value in self.construct_environment().items()
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

  def run(self, run_if_exists=False):
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
      commands                       = self.construct_command(),
      container_name                 = self.container_name,
      disable_image_prefetch         = False,
      disable_standard_error_capture = False,
      enable_fuse                    = False,
      environment                    = self.construct_environment(),
      ignore_exit_status             = False,
      image_uri                      = self.image_uri,
      publish_exposed_ports          = False,
      run_in_background              = False,
      timeout                        = self.get('TIMEOUT'),
    )

    # Pipeline Request
    pipeline = Pipeline( actions=[action], resources=resources, timeout=self.get('TIMEOUT') )
    pipeline_req = Request( pipeline=pipeline, pub_sub_topic=pub_sub_topic )

    # Start the pipeline
    start_pipeline(self.task.id, pipeline_req)
