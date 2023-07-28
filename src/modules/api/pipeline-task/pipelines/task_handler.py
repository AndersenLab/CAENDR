# Models
from caendr.models.datastore import DatabaseOperation, IndelPrimer, HeritabilityReport, NemascanMapping, Species
from caendr.models.error     import NotFoundError
from caendr.models.task      import DatabaseOperationTask, IndelPrimerTask, HeritabilityTask, NemaScanTask

# GCP
from caendr.models.lifesciences import ServiceAccount, VirtualMachine, Resources, Action, Pipeline, Request
from caendr.services.cloud.cloudrun import create_job_request, run_job_request
from caendr.services.cloud.lifesciences import start_pipeline

# Utils
from caendr.utils.env import get_env_var



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



class TaskHandler:

  # Associated Classes #
  # Overwrite in subclasses
  _Entity_Class = None
  _Task_Class   = None

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



  # Initialize from Task/Entity ID
  def __init__(self, **payload):
    self._task   = self._Task_Class(**payload)
    self._entity = self._Entity_Class(self.task.id, silent=False)

    if not self._entity._exists:
      raise NotFoundError(self._Entity_Class, {'id': self.task.id})


  # Task & Entity Objects #
  # Returning as properties prevents them from being set after init

  @property
  def task(self):
    return self._task

  @property
  def entity(self):
    return self._entity


  # Computed Properties #

  @property
  def kind(self):
    return self._Entity_Class.kind

  @property
  def container_name(self):
    return f'{self.kind}-{self.entity.id}'.lower().replace('_', '-')

  @property
  def container_version(self):
    return self.task.container_version

  @property
  def image_uri(self):
    return self.entity.get_container().uri()

  @property
  def latest_release(self):
    return Species.get(self.entity.species)['release_latest']
  
  @property
  def job_name(self):
    return self.container_name


  # Lookup Function #

  def get(self, key, default=None):
    return getattr(self, f'_{key}', default)


  # Functions for subclasses #

  def construct_environment(cls):
    if cls == TaskHandler:
      raise ValueError('Cannot call method construct_environment on base TaskHandler class')
    raise NotImplementedError()

  def construct_command(cls):
    if cls == TaskHandler:
      raise ValueError('Cannot call method construct_command on base TaskHandler class')
    raise NotImplementedError()
  

  def get_gcp_vars(self):
    return {
      "GOOGLE_SERVICE_ACCOUNT_EMAIL": sa_email,
      "GOOGLE_PROJECT":               GOOGLE_CLOUD_PROJECT_ID,
      "GOOGLE_ZONE":                  GOOGLE_CLOUD_ZONE,
    }
  
  def get_data_job_vars(self):
    return {
      "TRAIT_FILE": f"gs://{ self.entity.get_bucket_name() }/{ self.entity.get_data_blob_path() }",
      "WORK_DIR":   f"gs://{ WORK_BUCKET_NAME              }/{ self.entity.data_hash }",
      "DATA_DIR":   f"gs://{ self.entity.get_bucket_name() }/{ self.entity.get_input_data_path() }",
      "OUTPUT_DIR": f"gs://{ self.entity.get_bucket_name() }/{ self.entity.get_result_path() }",
    }


  # Run #

  def create_job(self):
    '''
      Create a CloudRun Job to run this task.
    '''
    request = create_job_request(**{
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
    return request.execute()


  def run_job(self):
    '''
      Initiate the CloudRun Job associated with this task.
    '''
    request = run_job_request(self.job_name)
    return request.execute()


  def start_pipeline(self):
    '''
      Create and run a VM for this task using Lifesciences

      Deprecated.
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





#
# Database Operation Pipeline
#
class DatabaseOperationTaskHandler(TaskHandler):

  _Entity_Class = DatabaseOperation
  _Task_Class   = DatabaseOperationTask

  _MACHINE_TYPE      = 'n1-standard-4'
  _BOOT_DISK_SIZE_GB = 50
  _VOLUME_NAME       = 'db_op_work'

  @property
  def _TIMEOUT(self):
    return '600s' if self.task.db_operation == 'TEST_ECHO' else '86400s'

  @property
  def _MEMORY_LIMITS(self):
    if self.task.db_operation == 'TEST_ECHO':
      return { 'memory': '512Mi', 'cpu': '1' }
    return { 'memory': '32Gi', 'cpu': '8' }

  @property
  def job_name(self):
    return f'db-op-{ self.task.db_operation.lower().replace("_", "-") }'

  def construct_command(self):
    return ['/db_operations/run.sh']

  def construct_environment(self):
    environment = self.task.args
    environment['DATABASE_OPERATION'] = self.task.db_operation
    environment['USERNAME']           = self.task.username if self.task.username else None
    environment['EMAIL']              = self.task.email    if self.task.email    else None
    environment['OPERATION_ID']       = self.entity.id
    environment['TASK_ID']            = self.task.id

    if self.task.args.get('SPECIES_LIST'):
      environment['SPECIES_LIST'] = ';'.join(self.task.args['SPECIES_LIST'])
    else:
      environment['SPECIES_LIST'] = None

    return environment





#
# Indel Finder Pipeline
#
class IndelFinderTaskHandler(TaskHandler):

  _Entity_Class = IndelPrimer
  _Task_Class   = IndelPrimerTask

  _BOOT_DISK_SIZE_GB = 20
  _TIMEOUT           = '3600s'

  def construct_command(self):
    return ['python', '/indel_primer/main.py']

  def construct_environment(self):
    return {
      "SPECIES":        self.entity['species'],
      "RELEASE":        self.entity['release'],
      "INDEL_STRAIN_1": self.entity['strain_1'],
      "INDEL_STRAIN_2": self.entity['strain_2'],
      "INDEL_SITE":     self.entity['site'],
      "RESULT_BUCKET":  self.entity.get_bucket_name(),
      "RESULT_BLOB":    self.entity.get_result_blob_path(),
    }



#
# Heritability Pipeline
#
class HeritabilityTaskHandler(TaskHandler):

  _Entity_Class = HeritabilityReport
  _Task_Class   = HeritabilityTask

  _BOOT_DISK_SIZE_GB = 10
  _TIMEOUT           = '9000s'

  def construct_command(self):
    if self.container_version == "v0.1a":
      return ['python', '/h2/main.py']
    return ["./heritability-nxf.sh"]

  def construct_environment(self):
    h2 = self.entity
  
    # TRAIT_FILE = f"gs://{MODULE_SITE_BUCKET_PRIVATE_NAME}/reports/heritability/{h2.container_version}/{h2.data_hash}/data.tsv"
    # WORK_DIR   = f"gs://{WORK_BUCKET_NAME}/{h2.data_hash}"
    # DATA_DIR   = f"gs://{DATA_BUCKET_NAME}/heritability"
    # OUTPUT_DIR = f"gs://{MODULE_SITE_BUCKET_PRIVATE_NAME}/reports/heritability/{h2.container_version}/{h2.data_hash}"

    # TODO: Make sure get_data_job_vars returns these values
    # TRAIT_FILE = f"gs://{ h2.get_bucket_name() }/{ h2.get_data_blob_path() }"
    # WORK_DIR   = f"gs://{ WORK_BUCKET_NAME     }/{ h2.data_hash }"
    # DATA_DIR   = f"gs://{DATA_BUCKET_NAME}/heritability"
    # OUTPUT_DIR = f"gs://{ h2.get_bucket_name() }/{ h2.get_blob_path() }"

    return {
      **self.get_gcp_vars(),
      **self.get_data_job_vars(),

      "SPECIES":        self.entity['species'],
      "VCF_VERSION":    self.latest_release,
      "DATA_HASH":      self.entity.data_hash,
      "DATA_BUCKET":    self.entity.get_bucket_name(),
      "DATA_BLOB_PATH": self.entity.get_blob_path(),
    }



#
# Nemascan Mapping Pipeline
#
class NemascanTaskHandler(TaskHandler):

  _Entity_Class = NemascanMapping
  _Task_Class   = NemaScanTask

  _BOOT_DISK_SIZE_GB = 100
  _TIMEOUT           = '86400s'

  def construct_command(self):
    return ['nemascan-nxf.sh']

  def construct_environment(self):
    # ns = self.entity

    # trait_file = f"gs://{ ns.get_bucket_name() }/{ ns.get_data_blob_path() }"
    # work_dir   = f"gs://{ WORK_BUCKET_NAME     }/{ ns.data_hash }"
    # data_dir   = f"gs://{ ns.get_bucket_name() }/{ ns.get_input_data_path() }"
    # output_dir = f"gs://{ ns.get_bucket_name() }/{ ns.get_result_path() }"

    return {
      **self.get_gcp_vars(),
      **self.get_data_job_vars(),

      "SPECIES":     self.entity['species'],
      "VCF_VERSION": self.latest_release,
      "USERNAME":    self.entity['username'],
      "EMAIL":       self.entity['email'],
    }
