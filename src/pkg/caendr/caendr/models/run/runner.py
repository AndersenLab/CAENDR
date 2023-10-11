# Built-in libraries
from abc import ABC, abstractmethod

# Logging
from caendr.services.logger import logger

# CaeNDR package
from caendr.models.datastore            import DataJobEntity, Species
from caendr.models.lifesciences         import ServiceAccount, VirtualMachine, Resources, Action, Pipeline, Request
from caendr.services.cloud.cloudrun     import create_job, run_job
from caendr.services.cloud.lifesciences import start_pipeline
from caendr.services.cloud.pubsub       import publish_message
from caendr.utils.env                   import get_env_var



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

  # TODO: Combine into a single run function, using task utils
  @abstractmethod
  def create_job(self): pass

  @abstractmethod
  def run_job(self): pass


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

  # Creating & Running Job #

  def create_job(self):
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


  def run_job(self):
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

  def create_job(self):
    pass

  def run_job(self):
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
